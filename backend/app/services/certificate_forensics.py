"""Certificate forgery detection — a *secondary* vision signal.

Loads the fine-tuned MobileNetV3-Small exported to ONNX by
``ml/notebooks/train_certificate_cnn.ipynb`` and scores an uploaded certificate
image (or the first page of a PDF) for visual forgery cues.

Design rules
------------
* **Secondary signal only.** The training set is 287 images and a
  width/height/file-size baseline still reaches ~0.63 ROC-AUC on the
  size-and-orientation-normalised data, so the model learns *this dataset*, not
  forgery in general.  Callers must therefore treat the result as supporting
  evidence: it may never, on its own, move a verdict or a risk band.
* **Degrade, never raise.** Missing ONNX file, missing ``onnxruntime``, missing
  Pillow, an unreadable upload or a PDF without a rasteriser all return
  ``available=False`` instead of an exception, so the pipeline keeps working on
  a fresh checkout before the model is trained.
* **Byte-for-byte inference parity.** Preprocessing mirrors training exactly:
  portrait orientation fix, short side scaled to ``normalise_max_side``, resize
  to ``input_size``, then per-channel ``(x - mean) / std``.  All of those values
  come from the JSON sidecar, so re-tuning never requires a code change.
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

MODEL_FILENAME = "certificate_cnn.onnx"
SIDECAR_FILENAME = "certificate_cnn.json"

# File extensions this service can decode directly.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")
PDF_SUFFIXES = (".pdf",)

# Preprocessing defaults, used only when the sidecar omits a key.
_DEFAULT_INPUT_SIZE = 224
_DEFAULT_MEAN = (0.485, 0.456, 0.406)
_DEFAULT_STD = (0.229, 0.224, 0.225)
_DEFAULT_MAX_SIDE = 384
_DEFAULT_THRESHOLD = 0.5

# Cached ONNX session + sidecar.  `_load_attempted` distinguishes "not loaded
# yet" from "tried and the artifacts are genuinely absent", so we warn once.
_session: Any | None = None
_config: dict[str, Any] | None = None
_load_attempted: bool = False


@dataclass(frozen=True)
class ForgerySignal:
    """Outcome of a certificate forgery check.

    Attributes:
        available: ``True`` only when the model ran and produced a probability.
        fake_probability: Model's ``p(forged)`` in ``[0, 1]``, or ``None``.
        threshold: Threshold used to decide :attr:`flagged`.
        flagged: ``True`` when ``fake_probability >= threshold``.
        notes: Human-readable explanation of what happened, including why the
            check was skipped when :attr:`available` is ``False``.
    """

    available: bool = False
    fake_probability: Optional[float] = None
    threshold: float = _DEFAULT_THRESHOLD
    flagged: bool = False
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Artifact discovery / model loading
# ---------------------------------------------------------------------------

def _find_artifacts_dir() -> Path:
    """Locate ``ml/artifacts`` from the repo layout or the working directory."""
    repo_root = Path(__file__).resolve().parents[3]
    candidate = repo_root / "ml" / "artifacts"
    if candidate.exists():
        return candidate

    for relative in ("ml/artifacts", "../ml/artifacts"):
        alternative = Path(relative).resolve()
        if alternative.exists():
            return alternative

    return candidate


def _validate_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a sidecar config with every key present and correctly typed.

    A partially written or hand-edited sidecar must not crash inference, so each
    field falls back to the training default when it is missing or malformed.
    """
    def _floats(key: str, default: tuple[float, ...]) -> tuple[float, ...]:
        values = raw.get(key)
        try:
            parsed = tuple(float(v) for v in values)  # type: ignore[union-attr]
        except (TypeError, ValueError):
            return default
        return parsed if len(parsed) == 3 else default

    input_size = raw.get("input_size")
    max_side = raw.get("normalise_max_side")
    threshold = raw.get("threshold")
    fake_index = raw.get("fake_index")

    return {
        "input_size": int(input_size) if isinstance(input_size, int) and input_size > 0 else _DEFAULT_INPUT_SIZE,
        "mean": _floats("mean", _DEFAULT_MEAN),
        "std": _floats("std", _DEFAULT_STD),
        "normalise_max_side": int(max_side) if isinstance(max_side, int) and max_side > 0 else _DEFAULT_MAX_SIDE,
        "normalise_orientation": bool(raw.get("normalise_orientation", True)),
        "threshold": float(threshold) if isinstance(threshold, (int, float)) else _DEFAULT_THRESHOLD,
        "fake_index": int(fake_index) if isinstance(fake_index, int) else 1,
        "classes": list(raw.get("classes") or ["real", "fake"]),
        "trained_on": str(raw.get("trained_on") or "unknown"),
        "pretrained": bool(raw.get("pretrained", False)),
    }


def load_model() -> tuple[Any | None, dict[str, Any] | None]:
    """Load and cache the ONNX session plus its sidecar configuration.

    Returns:
        ``(session, config)``, or ``(None, None)`` when ``onnxruntime`` is not
        installed or the artifacts have not been trained/committed yet.
    """
    global _session, _config, _load_attempted

    if _load_attempted:
        return _session, _config

    _load_attempted = True
    artifacts_dir = _find_artifacts_dir()
    model_path = artifacts_dir / MODEL_FILENAME
    sidecar_path = artifacts_dir / SIDECAR_FILENAME

    if not model_path.exists():
        logger.info(
            "Certificate CNN not found at %s — document analysis runs without the "
            "vision signal (train it with ml/notebooks/train_certificate_cnn.ipynb).",
            model_path,
        )
        return None, None

    try:
        import onnxruntime  # imported lazily: optional dependency
    except Exception as exc:  # pragma: no cover - depends on install
        logger.info(
            "onnxruntime not installed (%s) — skipping the certificate vision signal. "
            "Install it with: pip install -r backend/requirements.txt",
            exc,
        )
        return None, None

    try:
        raw_config: dict[str, Any] = {}
        if sidecar_path.exists():
            with open(sidecar_path, encoding="utf-8") as handle:
                raw_config = json.load(handle)
        config = _validate_config(raw_config)

        options = onnxruntime.SessionOptions()
        # One image per request: extra threads only add latency here.
        options.intra_op_num_threads = 1
        options.log_severity_level = 3  # suppress ONNX Runtime warnings

        _session = onnxruntime.InferenceSession(
            str(model_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        _config = config
        logger.info(
            "Certificate CNN loaded from %s (input=%d, threshold=%.3f, trained_on=%s).",
            model_path, config["input_size"], config["threshold"], config["trained_on"],
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to load the certificate CNN: %s", exc)
        _session, _config = None, None

    return _session, _config


def is_available() -> bool:
    """Return ``True`` when the model is loaded and ready for inference."""
    session, _ = load_model()
    return session is not None


def reset_cache() -> None:
    """Clear the cached session (used by tests and after re-deploying a model)."""
    global _session, _config, _load_attempted
    _session, _config, _load_attempted = None, None, False


# ---------------------------------------------------------------------------
# Decoding uploaded bytes into a PIL image
# ---------------------------------------------------------------------------

def _suffix_of(filename: str | None, document_bytes: bytes) -> str:
    """Best-effort file extension from the filename, falling back to magic bytes."""
    if filename:
        return Path(filename).suffix.lower()
    for magic, suffix in ((b"%PDF", ".pdf"), (b"\x89PNG", ".png"), (b"\xff\xd8", ".jpg")):
        if document_bytes.startswith(magic):
            return suffix
    return ""


def _rasterise_pdf(document_bytes: bytes) -> tuple[Any | None, str | None]:
    """Render the first PDF page to a PIL image.

    Uses ``pypdfium2`` when available (small wheel, no native build).  Text-only
    PDFs have no page bitmap, so the caller falls back to the text-based checks.
    """
    try:
        import pypdfium2
    except Exception:
        return None, "PDF supplied but pypdfium2 is not installed; visual check skipped."

    try:
        pdf = pypdfium2.PdfDocument(io.BytesIO(document_bytes))
        try:
            if len(pdf) == 0:
                return None, "PDF has no pages; visual check skipped."
            page = pdf[0]
            bitmap = page.render(scale=2.0)  # ~144 DPI, enough for a 224px input
            return bitmap.to_pil().convert("RGB"), None
        finally:
            pdf.close()
    except Exception as exc:
        logger.debug("PDF rasterisation failed: %s", exc)
        return None, f"Could not render the PDF page ({type(exc).__name__}); visual check skipped."


def _to_image(document_bytes: bytes, filename: str | None) -> tuple[Any | None, str | None]:
    """Convert upload bytes to a ``PIL.Image`` in RGB.

    Returns:
        ``(image, note)``.  On success ``note`` is ``None``; otherwise ``image``
        is ``None`` and ``note`` explains why.
    """
    suffix = _suffix_of(filename, document_bytes)

    if suffix in PDF_SUFFIXES:
        return _rasterise_pdf(document_bytes)

    try:
        from PIL import Image
    except Exception:
        return None, "Pillow is not installed; visual check skipped."

    try:
        with Image.open(io.BytesIO(document_bytes)) as handle:
            handle.load()
            return handle.convert("RGB"), None
    except Exception as exc:
        logger.debug("Image decode failed for %r: %s", filename, exc)
        return None, f"Upload could not be decoded as an image ({type(exc).__name__}); visual check skipped."


# ---------------------------------------------------------------------------
# Preprocessing (must mirror training)
# ---------------------------------------------------------------------------

def preprocess(image: Any, config: dict[str, Any]) -> Any:
    """Turn a PIL image into a normalised ``(1, 3, S, S)`` float32 batch.

    Mirrors the notebook's ``normalise_dataset`` + ``eval_tf`` exactly:
    rotate landscape scans portrait, scale so ``min(w, h) == normalise_max_side``,
    then resize to ``input_size`` and normalise per channel.
    """
    import numpy as np
    from PIL import Image

    input_size = int(config["input_size"])
    max_side = int(config["normalise_max_side"])
    mean = np.asarray(config["mean"], dtype=np.float32)
    std = np.asarray(config["std"], dtype=np.float32)

    prepared = image.convert("RGB")
    if config.get("normalise_orientation", True) and prepared.width > prepared.height:
        prepared = prepared.transpose(Image.ROTATE_90)

    if max_side > 0:
        scale = max_side / max(1, min(prepared.size))
        resized = (
            max(1, round(prepared.width * scale)),
            max(1, round(prepared.height * scale)),
        )
        prepared = prepared.resize(resized, Image.LANCZOS)

    prepared = prepared.resize((input_size, input_size), Image.BICUBIC)

    array = np.asarray(prepared, dtype=np.float32) / 255.0
    array = (array - mean.reshape(1, 1, 3)) / std.reshape(1, 1, 3)
    return np.transpose(array, (2, 0, 1))[None, ...].astype(np.float32)


def _softmax(values: Any) -> Any:
    """Numerically stable softmax over the last axis."""
    import numpy as np

    shifted = values - np.max(values, axis=-1, keepdims=True)
    exponentiated = np.exp(shifted)
    return exponentiated / np.sum(exponentiated, axis=-1, keepdims=True)


def _fake_probability(outputs: Any, fake_index: int) -> float:
    """Extract ``p(forged)`` from raw model output.

    Handles both a softmax output (which the exported graph already applies) and
    raw logits, so the service stays correct if the export changes.
    """
    import numpy as np

    values = np.asarray(outputs, dtype=np.float32).reshape(-1)
    total = float(values.sum())

    if np.all(values >= 0.0) and abs(total - 1.0) < 1e-3:
        probabilities = values  # already softmaxed
    else:
        probabilities = _softmax(values)

    index = fake_index if 0 <= fake_index < probabilities.size else probabilities.size - 1
    return float(probabilities[index])


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyse_document(
    document_bytes: bytes | None,
    filename: str | None = None,
) -> ForgerySignal:
    """Score an uploaded certificate (or the first PDF page) for forgery cues.

    Never raises: every failure path returns ``available=False`` with a note.

    Args:
        document_bytes: Raw bytes of the uploaded file.
        filename: Original filename, used to pick the decoder.

    Returns:
        A :class:`ForgerySignal`.  Callers must treat a result as *supporting*
        evidence only — it must not, by itself, change a risk band or verdict.
    """
    if not document_bytes:
        return ForgerySignal(notes=["No document supplied; visual check skipped."])

    session, config = load_model()
    if session is None or config is None:
        return ForgerySignal(
            notes=[
                "Certificate forgery model is not deployed; visual check skipped "
                "(document text checks still apply)."
            ]
        )

    image, note = _to_image(document_bytes, filename)
    if image is None:
        return ForgerySignal(
            threshold=float(config["threshold"]),
            notes=[note or "Unreadable upload."],
        )

    try:
        batch = preprocess(image, config)
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: batch})[0]
        probability = _fake_probability(outputs, int(config["fake_index"]))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Certificate inference failed: %s", exc)
        return ForgerySignal(
            threshold=float(config["threshold"]),
            notes=[f"Inference failed ({type(exc).__name__}); visual check skipped."],
        )

    threshold = float(config["threshold"])
    flagged = probability >= threshold

    notes = [
        f"Visual forgery model scored the certificate at {probability:.2f} "
        f"p(forged) against a {threshold:.2f} threshold."
    ]
    notes.append(
        "Secondary signal only: the model was trained on a small public dataset and "
        "may not generalise to this certificate."
    )
    if not config.get("pretrained", False):
        notes.append(
            "This model was trained from scratch (no ImageNet weights); its output is "
            "especially weak."
        )

    logger.info(
        "Certificate visual check: p(forged)=%.3f threshold=%.3f flagged=%s (file=%s)",
        probability, threshold, flagged, filename,
    )
    return ForgerySignal(
        available=True,
        fake_probability=round(probability, 4),
        threshold=threshold,
        flagged=flagged,
        notes=notes,
    )