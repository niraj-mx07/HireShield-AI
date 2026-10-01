"""Named-entity recognition (NER) for recruiter and job-listing text.

Entity extraction runs in two complementary layers:

1. **Structured identifiers** — deterministic regular expressions for emails,
   phone numbers, URLs, UPI handles, crypto wallet addresses, and monetary
   amounts.  These always run and never depend on an external model.
2. **Contextual named entities** — PERSON / ORG / LOCATION / DATE / MONEY
   entities produced by an NLP engine, chosen from the first available
   provider:

   * ``spaCy`` (``en_core_web_sm`` by default), else
   * ``Hugging Face Transformers`` token-classification
     (``dslim/bert-base-NER`` by default), else
   * no NER engine — structured identifiers are still returned.

The heavy NLP dependencies are imported lazily, so the backend boots fine
without them.  Install them with ``backend/requirements-nlp.txt``::

    pip install -r backend/requirements-nlp.txt
    python -m spacy download en_core_web_sm
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# Text longer than this is truncated before NLP inference to bound latency.
MAX_NER_CHARS = 20_000

# Cap on returned entities per extraction.
MAX_ENTITIES = 60

# Canonical label set surfaced to the API.
STRUCTURED_LABELS = ("EMAIL", "PHONE", "URL", "UPI_ID", "CRYPTO_WALLET", "MONEY")

# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Entity:
    """A single extracted entity.

    Attributes:
        text: The matched surface string.
        label: Normalised entity label (e.g. ``EMAIL``, ``PERSON``, ``ORG``).
        source: Which extractor produced it (``regex``, ``spacy``, or
            ``transformers``).
        confidence: Confidence in the range 0–1 (regex matches are 1.0).
    """

    text: str
    label: str
    source: str
    confidence: float = 1.0


@dataclass
class EntityExtraction:
    """Aggregated NER result for a piece of text."""

    provider: str
    entities: list[Entity] = field(default_factory=list)

    def by_label(self) -> dict[str, list[str]]:
        """Group entity surface strings by label, preserving insertion order."""
        grouped: dict[str, list[str]] = {}
        for entity in self.entities:
            grouped.setdefault(entity.label, [])
            if entity.text not in grouped[entity.label]:
                grouped[entity.label].append(entity.text)
        return grouped


# ---------------------------------------------------------------------------
# Layer 1 — structured identifiers (always on)
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_URL_RE = re.compile(r"\bhttps?://[^\s<>\"')]+|\bwww\.[^\s<>\"')]+")
# UPI handles carry no dot after '@' (that would make them email addresses).
# The negative lookahead stops the regex from matching only the part of an
# email address before the top-level dots (e.g. "hr.team@acme" out of
# "hr.team@acme-jobs.com").  A trailing sentence period is still allowed.
_UPI_RE = re.compile(r"\b[A-Za-z0-9._\-]{2,}@[A-Za-z]{2,32}(?![\-A-Za-z0-9])")
_CRYPTO_RE = re.compile(
    r"\b0x[a-fA-F0-9]{40}\b"                       # Ethereum / EVM
    r"|\bbc1[a-z0-9]{25,62}\b"                     # Bitcoin bech32
    r"|\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"        # Bitcoin legacy
    r"|\bT[1-9A-HJ-NP-Za-km-z]{33}\b"              # Tron TRC-20
)
_MONEY_RE = re.compile(
    r"\b(?:rs\.?|inr|usd|eur|gbp|₹|\$)\s?\d[\d,]*(?:\.\d+)?\b",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
_DIGITS_RE = re.compile(r"\d")
# Any Unicode letter — used to discard purely numeric contextual spans.
_ALPHA_RE = re.compile(r"[^\W\d_]", re.UNICODE)


def _structured_entities(text: str) -> list[Entity]:
    """Extract deterministic identifier entities from *text*."""
    if not text:
        return []

    entities: list[Entity] = []

    def _add(pattern: re.Pattern[str], label: str) -> list[str]:
        found: list[str] = []
        for match in pattern.finditer(text):
            value = match.group(0).strip()
            if value and value not in found:
                found.append(value)
                entities.append(Entity(text=value, label=label, source="regex", confidence=1.0))
        return found

    emails = _add(_EMAIL_RE, "EMAIL")
    _add(_URL_RE, "URL")
    _add(_CRYPTO_RE, "CRYPTO_WALLET")
    _add(_MONEY_RE, "MONEY")

    # UPI handles: exclude anything that is actually an email address.
    email_lower = {e.lower() for e in emails}
    for match in _UPI_RE.finditer(text):
        value = match.group(0).strip()
        if "@" not in value or "." in value.split("@", 1)[1]:
            continue
        if value.lower() in email_lower:
            continue
        if not any(e.text == value and e.label == "UPI_ID" for e in entities):
            entities.append(Entity(text=value, label="UPI_ID", source="regex", confidence=0.9))

    # Phone numbers: keep only candidates with a plausible digit count.
    for match in _PHONE_RE.finditer(text):
        value = match.group(0).strip()
        digit_count = len(_DIGITS_RE.findall(value))
        if 10 <= digit_count <= 15:
            entities.append(Entity(text=value, label="PHONE", source="regex", confidence=0.85))

    return entities


def _dedupe(entities: list[Entity]) -> list[Entity]:
    """Remove duplicate (label, text) pairs while preserving order."""
    seen: set[tuple[str, str]] = set()
    result: list[Entity] = []
    for entity in entities:
        key = (entity.label, entity.text.lower())
        if key not in seen:
            seen.add(key)
            result.append(entity)
    return result


def _filter_contextual(entities: list[Entity], structured: list[Entity]) -> list[Entity]:
    """Drop noisy contextual spans produced by the NER engine.

    Two classes of span add no value on top of the deterministic layer:

    * purely numeric spans (e.g. spaCy tagging ``5000`` or ``12/05/2024`` as
      ``DATE``/``MONEY``) — the regex layer already covers money and phones;
    * spans that repeat an identifier already found by the regex layer (e.g.
      a UPI handle also tagged as ``ORG``).
    """
    known_texts = {entity.text.strip().lower() for entity in structured}
    kept: list[Entity] = []
    for entity in entities:
        value = entity.text.strip()
        if not value or not _ALPHA_RE.search(value):
            continue
        if value.lower() in known_texts:
            continue
        kept.append(entity)
    return kept


# ---------------------------------------------------------------------------
# Layer 2 — contextual NER engines (spaCy -> Transformers -> none)
# ---------------------------------------------------------------------------

# spaCy entity labels mapped to our canonical vocabulary.
_SPACY_LABEL_MAP = {
    "PERSON": "PERSON",
    "ORG": "ORG",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "LOCATION",
    "NORP": "GROUP",
    "MONEY": "MONEY",
    "DATE": "DATE",
    "TIME": "DATE",
    "PRODUCT": "PRODUCT",
    "EVENT": "EVENT",
    "LAW": "LAW",
    "WORK_OF_ART": "WORK_OF_ART",
}

# Hugging Face (dslim/bert-base-NER) labels mapped to our canonical vocabulary.
_TRANSFORMERS_LABEL_MAP = {
    "PER": "PERSON",
    "ORG": "ORG",
    "LOC": "LOCATION",
    "MISC": "MISC",
}


@lru_cache(maxsize=1)
def _load_spacy():
    """Load and cache a spaCy pipeline, or ``None`` when unavailable."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.nlp_ner_enabled:
        return None
    try:
        import spacy
    except Exception as exc:
        logger.info("spaCy not available (%s); trying next NER provider.", exc)
        return None

    candidates = [settings.spacy_model, "en_core_web_sm"]
    for model_name in dict.fromkeys(c for c in candidates if c):
        try:
            nlp = spacy.load(model_name, disable=["lemmatizer"])
            logger.info("spaCy NER provider loaded with model '%s'.", model_name)
            return nlp
        except Exception as exc:
            logger.info("spaCy model '%s' unavailable: %s", model_name, exc)
    return None


@lru_cache(maxsize=1)
def _load_transformers():
    """Load and cache a Hugging Face NER pipeline, or ``None`` when unavailable."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.nlp_ner_enabled or not settings.transformers_ner_enabled:
        return None
    try:
        from transformers import pipeline
    except Exception as exc:
        logger.info("Hugging Face transformers not available (%s); skipping.", exc)
        return None
    try:
        ner = pipeline(
            "ner",
            model=settings.transformers_ner_model,
            aggregation_strategy="simple",
        )
        logger.info(
            "Hugging Face NER provider loaded with model '%s'.",
            settings.transformers_ner_model,
        )
        return ner
    except Exception as exc:
        logger.info("Transformer NER model load failed: %s", exc)
        return None


def _spacy_entities(nlp, text: str) -> list[Entity]:
    """Run spaCy NER and map labels into the canonical vocabulary."""
    entities: list[Entity] = []
    try:
        for ent in nlp(text).ents:
            label = _SPACY_LABEL_MAP.get(ent.label_)
            if not label:
                continue
            entities.append(
                Entity(text=ent.text.strip(), label=label, source="spacy", confidence=0.80)
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("spaCy NER inference failed: %s", exc)
    return entities


def _transformers_entities(ner, text: str) -> list[Entity]:
    """Run the Hugging Face NER pipeline and map labels canonically."""
    entities: list[Entity] = []
    try:
        for ent in ner(text):
            raw_label = str(ent.get("entity_group") or ent.get("entity") or "")
            label = _TRANSFORMERS_LABEL_MAP.get(raw_label.replace("B-", "").replace("I-", ""))
            if not label:
                continue
            value = str(ent.get("word", "")).strip()
            if not value:
                continue
            entities.append(
                Entity(
                    text=value,
                    label=label,
                    source="transformers",
                    confidence=round(float(ent.get("score", 0.0)), 2),
                )
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Transformer NER inference failed: %s", exc)
    return entities


def _run_ner_engine(text: str) -> tuple[str, list[Entity]]:
    """Return ``(provider_name, entities)`` from the first working NER engine."""
    nlp = _load_spacy()
    if nlp is not None:
        return "spacy", _spacy_entities(nlp, text)

    ner = _load_transformers()
    if ner is not None:
        return "transformers", _transformers_entities(ner, text)

    return "regex", []


def extract_entities(text: Optional[str]) -> EntityExtraction:
    """Extract structured identifiers and contextual named entities.

    Args:
        text: Free-form text (job description, recruiter message, document
            body, or retrieved page text).  ``None``/empty input yields an
            empty result.

    Returns:
        An :class:`EntityExtraction` whose ``provider`` is one of ``"spacy"``,
        ``"transformers"``, or ``"regex"``.  This function never raises.
    """
    if not text or not text.strip():
        return EntityExtraction(provider="regex", entities=[])

    try:
        entities: list[Entity] = _structured_entities(text)

        trimmed = text[:MAX_NER_CHARS]
        provider, ner_entities = _run_ner_engine(trimmed)
        entities.extend(_filter_contextual(ner_entities, entities))

        entities = _dedupe(entities)[:MAX_ENTITIES]
        return EntityExtraction(provider=provider, entities=entities)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Entity extraction failed: %s", exc, exc_info=True)
        return EntityExtraction(provider="regex", entities=[])

