"""Tests for the certificate forgery vision service.

These tests never require the Kaggle-trained ``certificate_cnn.onnx``: the model
file is mocked or the artifacts directory is redirected to an empty temp folder,
so a fresh checkout and CI both pass before training has run.
"""

from __future__ import annotations

import io
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from app.services import certificate_forensics as cf

# ImageNet statistics the notebook ships in `certificate_cnn.json`.
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def _config(**overrides) -> dict:
    """Return a valid sidecar config, with optional overrides."""
    config = {
        "input_size": 224,
        "mean": MEAN,
        "std": STD,
        "normalise_max_side": 384,
        "normalise_orientation": True,
        "threshold": 0.5,
        "fake_index": 1,
        "classes": ["real", "fake"],
        "trained_on": "test",
        "pretrained": True,
    }
    config.update(overrides)
    return config


class _StubSession:
    """Minimal stand-in for ``onnxruntime.InferenceSession``."""

    def __init__(self, outputs, exc: Exception | None = None):
        self._outputs = outputs
        self._exc = exc
        self.calls: list[np.ndarray] = []

    def get_inputs(self):
        return [SimpleNamespace(name="X")]

    def run(self, output_names, input_feed):
        if self._exc is not None:
            raise self._exc
        batch = input_feed["X"]
        self.calls.append(batch)
        return [self._outputs]


def _png_bytes(color=(120, 130, 140), size=(64, 48)) -> bytes:
    """Return a small PNG payload."""
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def _clean_cache():
    """Keep the module-level ONNX session cache from leaking between tests."""
    cf.reset_cache()
    yield
    cf.reset_cache()


# ---------------------------------------------------------------------------
# Graceful degradation — the important case before the model is trained
# ---------------------------------------------------------------------------

def test_no_model_file_degrades_without_raising(tmp_path, monkeypatch):
    """A missing .onnx file must not raise; the vision step is simply skipped."""
    monkeypatch.setattr(cf, "_find_artifacts_dir", lambda: tmp_path)

    signal = cf.analyse_document(_png_bytes(), "certificate.png")

    assert signal.available is False
    assert signal.fake_probability is None
    assert signal.flagged is False
    assert "not deployed" in signal.notes[0]


def test_is_available_false_when_artifacts_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cf, "_find_artifacts_dir", lambda: tmp_path)
    assert cf.is_available() is False


def test_no_document_bytes_skips():
    signal = cf.analyse_document(None, "certificate.png")
    assert signal.available is False
    assert "No document supplied" in signal.notes[0]


def test_unreadable_upload_returns_note_not_exception(monkeypatch):
    """Garbage bytes with a model present must return a note, never raise."""
    monkeypatch.setattr(cf, "load_model", lambda: (_StubSession([[0.4, 0.6]]), _config()))

    signal = cf.analyse_document(b"this is definitely not an image", "notes.txt")

    assert signal.available is False
    assert "could not be decoded" in signal.notes[0]


def test_empty_document_bytes_skips():
    assert cf.analyse_document(b"") .available is False


# ---------------------------------------------------------------------------
# Sidecar validation
# ---------------------------------------------------------------------------

def test_malformed_sidecar_falls_back_to_training_defaults():
    """A hand-edited or truncated sidecar must not break inference."""
    config = cf._validate_config(
        {"input_size": "big", "mean": "oops", "std": None, "threshold": None,
         "normalise_max_side": -1, "fake_index": "fake"}
    )

    assert config["input_size"] == 224
    assert config["mean"] == (0.485, 0.456, 0.406)
    assert config["std"] == (0.229, 0.224, 0.225)
    assert config["threshold"] == 0.5
    assert config["normalise_max_side"] == 384
    assert config["fake_index"] == 1


def test_sidecar_values_are_used_when_valid():
    config = cf._validate_config(
        {"input_size": 224, "threshold": 0.72, "normalise_max_side": 512,
         "normalise_orientation": False, "pretrained": False, "classes": ["genuine", "forged"]}
    )

    assert config["threshold"] == 0.72
    assert config["normalise_max_side"] == 512
    assert config["normalise_orientation"] is False
    assert config["pretrained"] is False
    assert config["classes"] == ["genuine", "forged"]


# ---------------------------------------------------------------------------
# Preprocessing parity with training
# ---------------------------------------------------------------------------

def test_preprocess_shape_dtype_and_normalisation_values():
    """Uniform grey 128 must normalise to exactly (128/255 - mean) / std."""
    batch = cf.preprocess(Image.new("RGB", (300, 400), (128, 128, 128)), _config())

    assert batch.shape == (1, 3, 224, 224)
    assert batch.dtype == np.float32

    grey = 128 / 255.0
    for channel in range(3):
        expected = (grey - MEAN[channel]) / STD[channel]
        assert float(batch[0, channel, 0, 0]) == pytest.approx(expected, abs=1e-5)


def test_preprocess_rotates_landscape_to_portrait():
    """A landscape scan must preprocess identically to its rotated twin."""
    landscape = Image.new("RGB", (200, 100), (10, 20, 30))
    landscape.paste(Image.new("RGB", (100, 100), (240, 240, 240)), (100, 0))

    as_uploaded = cf.preprocess(landscape, _config())
    pre_rotated = cf.preprocess(landscape.transpose(Image.ROTATE_90), _config())

    np.testing.assert_allclose(as_uploaded, pre_rotated, atol=1e-5)


def test_preprocess_leaves_orientation_alone_when_disabled():
    landscape = Image.new("RGB", (200, 100), (10, 20, 30))
    landscape.paste(Image.new("RGB", (100, 100), (240, 240, 240)), (100, 0))

    as_uploaded = cf.preprocess(landscape, _config(normalise_orientation=False))
    pre_rotated = cf.preprocess(landscape.transpose(Image.ROTATE_90), _config())

    assert not np.allclose(as_uploaded, pre_rotated, atol=1e-3)


def test_preprocess_upgrades_small_images_to_common_short_side():
    """A 40x30 thumbnail and a 1200x900 scan end up at the same model input."""
    small = cf.preprocess(Image.new("RGB", (40, 30), (200, 100, 50)), _config())
    large = cf.preprocess(Image.new("RGB", (1200, 900), (200, 100, 50)), _config())

    assert small.shape == large.shape == (1, 3, 224, 224)
    # Same flat colour, so rescaling cannot change the normalised values.
    np.testing.assert_allclose(small, large, atol=1e-5)


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

def test_fake_probability_reads_softmax_output():
    assert cf._fake_probability(np.array([[0.75, 0.25]]), 1) == pytest.approx(0.25)
    assert cf._fake_probability(np.array([[0.75, 0.25]]), 0) == pytest.approx(0.75)


def test_fake_probability_applies_softmax_to_raw_logits():
    """Logits must be softmaxed, otherwise out-of-range probabilities leak out."""
    probability = cf._fake_probability(np.array([[-2.0, 3.0]]), 1)
    assert probability == pytest.approx(1 / (1 + np.exp(-5.0)), abs=1e-4)


def test_fake_probability_tolerates_out_of_range_fake_index():
    """A bogus fake_index falls back to the last class instead of raising."""
    assert cf._fake_probability(np.array([[0.4, 0.6]]), 99) == pytest.approx(0.6)


# ---------------------------------------------------------------------------
# End-to-end inference (mocked session — no Kaggle artifact needed)
# ---------------------------------------------------------------------------

def test_flagged_when_probability_at_or_above_threshold(monkeypatch):
    session = _StubSession([[0.2, 0.8]])
    monkeypatch.setattr(cf, "load_model", lambda: (session, _config(threshold=0.5)))

    signal = cf.analyse_document(_png_bytes(), "certificate.png")

    assert signal.available is True
    assert signal.fake_probability == pytest.approx(0.8)
    assert signal.flagged is True
    assert "Secondary signal only" in signal.notes[1]
    assert session.calls[0].shape == (1, 3, 224, 224)


def test_not_flagged_below_threshold(monkeypatch):
    monkeypatch.setattr(cf, "load_model", lambda: (_StubSession([[0.9, 0.1]]), _config()))

    signal = cf.analyse_document(_png_bytes(), "certificate.png")

    assert signal.available is True
    assert signal.flagged is False


def test_threshold_boundary_is_inclusive(monkeypatch):
    """p == threshold counts as flagged, matching the notebook's >= comparison."""
    monkeypatch.setattr(cf, "load_model", lambda: (_StubSession([[0.5, 0.5]]), _config(threshold=0.5)))

    assert cf.analyse_document(_png_bytes(), "c.png").flagged is True


def test_threshold_from_sidecar_is_respected(monkeypatch):
    """Raising the threshold in the sidecar must lower the flag rate, no code change."""
    monkeypatch.setattr(cf, "load_model", lambda: (_StubSession([[0.3, 0.7]]), _config(threshold=0.8)))

    signal = cf.analyse_document(_png_bytes(), "c.png")

    assert signal.threshold == 0.8
    assert signal.flagged is False


def test_inference_failure_degrades(monkeypatch):
    """An ONNX runtime error must be reported, not propagated."""
    session = _StubSession([[0.5, 0.5]], exc=RuntimeError("bad tensor"))
    monkeypatch.setattr(cf, "load_model", lambda: (session, _config()))

    signal = cf.analyse_document(_png_bytes(), "c.png")

    assert signal.available is False
    assert "Inference failed" in signal.notes[0]


def test_untrusted_model_adds_an_honesty_note(monkeypatch):
    """A from-scratch model (no ImageNet weights) must say so in the findings."""
    monkeypatch.setattr(
        cf, "load_model", lambda: (_StubSession([[0.1, 0.9]]), _config(pretrained=False))
    )

    signal = cf.analyse_document(_png_bytes(), "c.png")

    assert any("trained from scratch" in note for note in signal.notes)


def test_pdf_without_rasterisable_page_degrades(monkeypatch, tmp_path):
    """A broken/text-only PDF must not raise; the text checks still run."""
    monkeypatch.setattr(cf, "load_model", lambda: (_StubSession([[0.5, 0.5]]), _config()))

    signal = cf.analyse_document(b"%PDF-1.4\nnot really a pdf", "certificate.pdf")

    assert signal.available is False
    assert "visual check skipped" in signal.notes[0]