"""Tests for the two-layer NLP entity extraction service.

Layer 1 (deterministic regex identifiers) is always exercised.  Layer 2
(spaCy / Transformers) is optional, so provider tests skip cleanly when the
model dependencies are not installed.
"""

from __future__ import annotations

import pytest

from app.services import nlp_entities

SAMPLE_TEXT = (
    "URGENT HIRING! Email hr.team@acme-jobs.com or call +91 98765 43210. "
    "Registration fee Rs 5000 is required. UPI: acmepayments@okhdfcbank. "
    "Wallet: 0x1234567890abcdef1234567890abcdef12345678. "
    "Apply at https://acme-jobs.com/apply-now today."
)


@pytest.fixture
def nlp_disabled(monkeypatch):
    """Force regex-only mode for the duration of a test."""
    from app.config import get_settings

    monkeypatch.setenv("NLP_NER_ENABLED", "false")
    get_settings.cache_clear()
    nlp_entities._load_spacy.cache_clear()
    nlp_entities._load_transformers.cache_clear()
    yield
    get_settings.cache_clear()
    nlp_entities._load_spacy.cache_clear()
    nlp_entities._load_transformers.cache_clear()


# ---------------------------------------------------------------------------
# Layer 1 — deterministic structured identifiers
# ---------------------------------------------------------------------------


def test_structured_identifiers_are_extracted():
    """Emails, phones, URLs, UPI ids, wallets, and money are all detected."""
    result = nlp_entities.extract_entities(SAMPLE_TEXT)
    labels = {entity.label for entity in result.entities}

    for expected in ("EMAIL", "PHONE", "URL", "UPI_ID", "CRYPTO_WALLET", "MONEY"):
        assert expected in labels, f"missing {expected} in {sorted(labels)}"


def test_structured_identifiers_have_regex_source_and_confidence():
    """Structured matches are tagged with their extractor and confidence."""
    result = nlp_entities.extract_entities(SAMPLE_TEXT)
    emails = [e for e in result.entities if e.label == "EMAIL"]

    assert emails, "expected at least one EMAIL entity"
    assert all(e.source == "regex" for e in emails)
    assert all(0.0 < e.confidence <= 1.0 for e in emails)
    assert emails[0].text == "hr.team@acme-jobs.com"


def test_email_is_not_misclassified_as_upi():
    """An email address must not also produce a partial UPI handle."""
    result = nlp_entities.extract_entities("Reach the recruiter at hr.team@acme-jobs.com.")
    labels = {e.label for e in result.entities}

    assert "EMAIL" in labels
    assert "UPI_ID" not in labels


def test_upi_handle_without_domain_dot_detected():
    """A bare UPI handle (no dot after '@') is recognised."""
    result = nlp_entities.extract_entities("Pay the deposit to acmepayments@okhdfcbank now.")
    upi = [e for e in result.entities if e.label == "UPI_ID"]

    assert any(e.text == "acmepayments@okhdfcbank" for e in upi)


def test_repeated_identifiers_are_deduplicated():
    """The same identifier appearing twice yields a single entity."""
    text = "Mail hr@acme.com first, then hr@acme.com again."
    result = nlp_entities.extract_entities(text)
    emails = [e for e in result.entities if e.label == "EMAIL"]

    assert len(emails) == 1


def test_by_label_groups_entities():
    """EntityExtraction.by_label groups surface strings by label."""
    grouped = nlp_entities.extract_entities(SAMPLE_TEXT).by_label()

    assert "hr.team@acme-jobs.com" in grouped.get("EMAIL", [])
    assert "https://acme-jobs.com/apply-now" in grouped.get("URL", [])


def test_empty_and_blank_text_yield_empty_result():
    """Empty input returns no entities and never raises."""
    for value in (None, "", "   \n\t "):
        result = nlp_entities.extract_entities(value)
        assert result.entities == []
        assert result.provider == "regex"


# ---------------------------------------------------------------------------
# Layer 2 — provider selection
# ---------------------------------------------------------------------------


def test_regex_provider_when_nlp_disabled(nlp_disabled):
    """With NER disabled the provider is 'regex' and identifiers still work."""
    result = nlp_entities.extract_entities(SAMPLE_TEXT)

    assert result.provider == "regex"
    assert all(e.source == "regex" for e in result.entities)
    assert any(e.label == "EMAIL" for e in result.entities)


def test_spacy_provider_selected_when_model_available():
    """spaCy wins provider selection and yields contextual entities."""
    nlp = nlp_entities._load_spacy()
    if nlp is None:
        pytest.skip("spaCy model not installed; provider falls back by design")

    result = nlp_entities.extract_entities(
        "Ravi Kumar works at Acme Corporation in Bengaluru and joined in 2024."
    )

    assert result.provider == "spacy"
    assert any(
        e.label in ("PERSON", "ORG", "LOCATION", "DATE") for e in result.entities
    )


# ---------------------------------------------------------------------------
# Contextual-noise filtering
# ---------------------------------------------------------------------------


def test_contextual_noise_filter_is_deterministic():
    """Numeric-only spans and identifier duplicates are discarded."""
    structured = [
        nlp_entities.Entity(
            text="acmepayments@okhdfcbank", label="UPI_ID", source="regex", confidence=0.9
        )
    ]
    candidates = [
        nlp_entities.Entity(text="5000", label="DATE", source="spacy", confidence=0.8),
        nlp_entities.Entity(text="12/05/2024", label="DATE", source="spacy", confidence=0.8),
        nlp_entities.Entity(
            text="acmepayments@okhdfcbank", label="ORG", source="spacy", confidence=0.8
        ),
        nlp_entities.Entity(text="Ravi Kumar", label="PERSON", source="spacy", confidence=0.8),
    ]

    kept = nlp_entities._filter_contextual(candidates, structured)

    assert [entity.text for entity in kept] == ["Ravi Kumar"]


def test_spacy_noise_is_filtered_from_results():
    """Model output never contains numeric-only spans or duplicate handles."""
    if nlp_entities._load_spacy() is None:
        pytest.skip("spaCy model not installed; provider falls back by design")

    result = nlp_entities.extract_entities(
        "Paid Rs 5000 on 12/05/2024. UPI: acmepayments@okhdfcbank."
    )

    for entity in result.entities:
        assert any(ch.isalpha() for ch in entity.text), entity

    upi = [e for e in result.entities if e.text.lower() == "acmepayments@okhdfcbank"]
    assert len(upi) == 1
    assert upi[0].label == "UPI_ID"
