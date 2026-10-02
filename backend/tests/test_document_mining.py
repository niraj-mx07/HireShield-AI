"""Unit tests for document-derived request fields (``document_mining``).

The miner copies information an uploaded offer letter already contains
(company name, listing URL, recruiter contacts) into the request fields the
user left blank.  These tests pin down the two safety properties:

* values are only produced when they are genuinely present and plausible;
* user-typed input is never overridden.
"""

from __future__ import annotations

from app.models.schemas import AssessmentRequest
from app.services import document_mining
from app.services.nlp_entities import Entity


OFFER_LETTER = (
    "OFFER OF EMPLOYMENT\n"
    "\n"
    "Company: Global Fast Data Entry Services Ltd\n"
    "Website: https://globalfastdataentry.example.com/careers\n"
    "\n"
    "Dear Candidate,\n"
    "You have been selected for the Data Entry Operator role.\n"
    "Apply before joining by contacting hr.team@acme-jobs.com or\n"
    "call +91 98765 43210 for assistance.\n"
    "\n"
    "A refundable registration fee of Rs 5000 is required to process\n"
    "your onboarding kit.\n"
)


# ---------------------------------------------------------------------------
# mine_document_fields
# ---------------------------------------------------------------------------


def test_mines_labelled_company_and_identifiers():
    found = document_mining.mine_document_fields(OFFER_LETTER)

    assert found["company_name"] == "Global Fast Data Entry Services Ltd"
    assert found["recruiter_email"] == "hr.team@acme-jobs.com"
    assert found["recruiter_phone"] == "+91 98765 43210"
    assert found["url"] == "https://globalfastdataentry.example.com/careers"


def test_www_url_is_normalised_to_https():
    found = document_mining.mine_document_fields(
        "Apply at www.example-org.com/apply now."
    )
    assert found["url"] == "https://www.example-org.com/apply"


def test_labelled_company_survives_prose_tail():
    """``Company: Acme Ltd is pleased...`` must not swallow the sentence."""
    found = document_mining.mine_document_fields(
        "Company: Acme Ltd is pleased to offer you the role."
    )
    assert found["company_name"] == "Acme Ltd"


def test_markdown_label_prefixes_are_tolerated():
    found = document_mining.mine_document_fields("**Company:** Zenith Staffing Pvt Ltd")
    assert found["company_name"] == "Zenith Staffing Pvt Ltd"


def test_empty_text_yields_no_fields():
    assert document_mining.mine_document_fields(None) == {}
    assert document_mining.mine_document_fields("   ") == {}


def test_plain_text_does_not_invent_fields():
    """No identifiers, no label → nothing is returned (no guessing)."""
    found = document_mining.mine_document_fields(
        "We are hiring for a remote data entry role. Flexible hours."
    )
    assert found == {}


# ---------------------------------------------------------------------------
# Company plausibility helpers
# ---------------------------------------------------------------------------


def test_org_entity_used_when_no_label_present():
    entities = [
        Entity(text="Zenith Staffing Solutions", label="ORG", source="spacy", confidence=0.9),
    ]
    assert (
        document_mining._company_from_entities(entities)
        == "Zenith Staffing Solutions"
    )


def test_non_org_entities_are_ignored_for_company():
    entities = [
        Entity(text="Mumbai", label="LOCATION", source="spacy", confidence=0.9),
        Entity(text="Rahul Verma", label="PERSON", source="spacy", confidence=0.9),
    ]
    assert document_mining._company_from_entities(entities) is None


def test_implausible_company_values_are_rejected():
    assert not document_mining._is_plausible_company("")
    assert not document_mining._is_plausible_company("A")
    assert not document_mining._is_plausible_company("the company")
    assert not document_mining._is_plausible_company("https://example.com")
    assert not document_mining._is_plausible_company("hr@example.com")
    assert not document_mining._is_plausible_company("Order 45219")
    assert document_mining._is_plausible_company("Acme Recruiters Pvt Ltd")


# ---------------------------------------------------------------------------
# fill_missing_fields — never override the user
# ---------------------------------------------------------------------------


def test_fill_sets_empty_fields_and_reports_names():
    request = AssessmentRequest()

    filled = document_mining.fill_missing_fields(request, OFFER_LETTER)

    assert filled == list(document_mining.DERIVABLE_FIELDS)
    assert request.company_name == "Global Fast Data Entry Services Ltd"
    assert request.url == "https://globalfastdataentry.example.com/careers"
    assert request.recruiter_email == "hr.team@acme-jobs.com"
    assert request.recruiter_phone == "+91 98765 43210"


def test_user_typed_values_are_never_overridden():
    request = AssessmentRequest(
        company_name="Typed By User Ltd",
        recruiter_email="typed@example.com",
    )

    filled = document_mining.fill_missing_fields(request, OFFER_LETTER)

    assert request.company_name == "Typed By User Ltd"
    assert request.recruiter_email == "typed@example.com"
    assert "company_name" not in filled
    assert "recruiter_email" not in filled
    assert "url" in filled  # untouched fields still get derived


def test_fill_with_no_document_is_a_noop():
    request = AssessmentRequest(company_name="Acme")

    assert document_mining.fill_missing_fields(request, None) == []
    assert request.company_name == "Acme"


# ---------------------------------------------------------------------------
# Document headings must never be mined as the hiring company
#
# spaCy tags an offer letter's block-style title ("OFFER OF EMPLOYMENT") as
# ORG with high confidence, and it appears *before* the real company name.  When
# it won, the company-verification analyzer was handed a document title as if it
# were the employer, inventing an unmatchable-company risk factor.
# ---------------------------------------------------------------------------

def test_document_heading_is_not_a_company():
    for heading in (
        "OFFER OF EMPLOYMENT",
        "APPOINTMENT LETTER",
        "EMPLOYMENT CONTRACT",
        "CERTIFICATE OF EXPERIENCE",
    ):
        assert document_mining._is_document_heading(heading) is True
        assert document_mining._is_plausible_company(heading) is False


def test_heading_containing_a_title_word_is_still_a_real_company():
    """A real all-caps name that merely contains a title word must survive."""
    value = "ACME EMPLOYMENT SOLUTIONS PVT LTD"
    assert document_mining._is_document_heading(value) is False
    assert document_mining._is_plausible_company(value) is True


def test_heading_entity_loses_to_the_real_company():
    """The regression that shipped: heading ORG first, real name later."""
    entities = [
        Entity(text="OFFER OF EMPLOYMENT", label="ORG", source="spacy", confidence=0.8),
        Entity(text="Software", label="ORG", source="spacy", confidence=0.8),
        Entity(
            text="Acme Corp.\nCompany\nAcme Corp",
            label="ORG",
            source="spacy",
            confidence=0.8,
        ),
    ]

    # The multi-line NER artefact spans a sentence and a table row, so it is
    # not a usable name; the heading is rejected outright.  Nothing is invented.
    assert document_mining._company_from_entities(entities) is None


def test_multiline_ner_artifact_is_rejected():
    assert document_mining._is_plausible_company("Acme Corp.\nCompany\nAcme Corp") is False


def test_two_line_table_label_is_mined():
    """docx/PDF tables put the label and its value on consecutive lines."""
    text = "OFFER OF EMPLOYMENT\nWe are pleased to offer you the role of Engineer at Acme Corp.\nCompany\nAcme Corp"

    assert document_mining._company_from_label(text) == "Acme Corp"
    assert document_mining.mine_document_fields(text)["company_name"] == "Acme Corp"
