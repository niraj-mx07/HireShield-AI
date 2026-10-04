"""Clause-level negation scope — separating *active mechanics* from *passive warnings*.

Why this module exists
----------------------
The risk analyzers match fraud mechanics with keyword regexes: ``registration
fee``, ``issue a check``, ``whatsapp``, ``security deposit``.  Those keywords
appear in two very different situations:

* **Active** — the employer *performs* the action.
  *"We will mail you a cashier's check to buy equipment from our vendor portal."*
* **Passive / protective** — the employer *forbids* or *warns against* it.
  *"Infosys never issues financial checks."* /
  *"We never conduct interviews over anonymous chat applications such as
  WhatsApp."* /
  *"We will never ask you to pay a registration fee."*

A keyword-only matcher scores both identically, so a legitimate corporate
anti-fraud notice was reported as *DON'T APPLY (80/100)* with "financial scam"
and "chat-app redirection" HIGH factors.  That is a false accusation against a
real employer, so the engine must not emit it.

How it decides
--------------
:func:`is_passive_reference` locates the *clause* containing a match and asks a
single question: **does the clause deny the mechanic, or instruct it?**

* A clause is bounded by sentence terminators **and** by contrastive
  connectives (``but``, ``however``, ``instead`` …), so a denial in one clause
  never launders a demand in the next one.
* A **strong denial** (``never``, ``do not``, ``will not``, ``under no
  circumstances`` …) protects the whole clause, unless the clause also carries a
  **directive** aimed at the reader (``you must pay``, ``please download``,
  ``within 24 hours``, ``we will mail you`` …).
* A **weak denial** (``no``, ``without``, ``zero``, ``free``) protects the clause
  only when nothing re-asserts the demand afterwards
  (``, just pay the registration fee``) and the match is not merely the
  complement of the denial (``no requirement to pay a fee``).

The evasion guard
-----------------
The protection is deliberately **clause-scoped, never global**.  Appending
*"we never ask for fees"* to an otherwise fraudulent offer letter does not and
must not neutralise the real demand sitting in the next sentence — only a global
"if a disclaimer exists, PASS" override would allow that, and
``backend/tests/test_negation_scope.py`` pins the evasion case shut.
"""

from __future__ import annotations

import re
from typing import Iterator

__all__ = [
    "is_passive_reference",
    "iter_active_matches",
    "first_active_match",
    "has_active_match",
    "find_negation_cue",
]


# ---------------------------------------------------------------------------
# Clause segmentation
# ---------------------------------------------------------------------------

# Characters that introduce a list item rather than continuing a sentence.
_LIST_MARKERS = "-–—•*#>·"

# Characters that can only end a sentence.
_TERMINATORS = ".!?;"


def _sentence_boundaries(text: str) -> list[int]:
    """Return the offsets at which sentences begin/end in ``text``.

    Extracted text from PDF / DOCX is *hard-wrapped*: a single sentence is split
    across several source lines, and the wrap point can fall right before a
    proper noun ("…chat applications such as\\nWhatsApp").  Splitting there
    would hide the governing ``never`` in a neighbouring clause and re-open the
    false positive this module exists to close.

    A newline is therefore treated as **soft** — a line wrap, not a sentence
    break — when all of the following hold:

    * it is a single newline (a blank line is always a hard break);
    * the previous non-space character is not a sentence terminator, so the
      sentence was not already finished;
    * the next character is not a list marker.
    """
    bounds: list[int] = [0]
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in _TERMINATORS:
            j = i + 1
            while j < n and text[j] in _TERMINATORS:
                j += 1
            bounds.append(j)
            i = j
            continue
        if ch == "\n":
            j = i + 1
            while j < n and text[j] == "\n":
                j += 1
            # Two or more newlines = paragraph break.
            if j - i > 1:
                bounds.append(j)
                i = j
                continue
            prev = text[:i].rstrip()
            prev_char = prev[-1] if prev else ""
            next_char = text[j:j + 1]
            if prev_char and prev_char not in _TERMINATORS and next_char not in _LIST_MARKERS:
                i = j  # hard-wrapped line: the sentence continues
                continue
            bounds.append(j)
            i = j
            continue
        i += 1
    bounds.append(n)
    return bounds


def _bounds_around(bounds: list[int], index: int) -> tuple[int, int]:
    """Return the ``[start, end)`` segment containing ``index``."""
    start = 0
    for b in bounds:
        if b <= index:
            start = b
        else:
            break
    for b in bounds:
        if b > index:
            return start, b
    return start, len(bounds) and bounds[-1]

# Contrastive / re-opening connectives.  "we never charge fees, **but** you must
# pay a deposit" is two clauses, not one denial.
_CONTRASTIVE_RE = re.compile(
    r"\b(?:but|however|instead|nevertheless|nonetheless|that\s+said|"
    r"otherwise|aside\s+from|apart\s+from|meanwhile|although|though|whereas|"
    r"and\s+(?=(?:you|the\s+candidate|the\s+applicant|applicants?)\s+"
    r"(?:must|should|shall|need|have|will|are|is)\b))\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Negation cues
# ---------------------------------------------------------------------------

# Strong denial: the speaker refuses the mechanic outright, for the whole clause.
_STRONG_DENIAL_RE = re.compile(
    r"\b(?:"
    r"never|"
    r"do\s+not|does\s+not|did\s+not|don'?t|doesn'?t|didn'?t|"
    r"will\s+not|won'?t|shall\s+not|shan'?t|"
    r"can\s+not|can'?t|cannot|"
    r"under\s+no\s+circumst\w+|"
    r"no\s+one\s+will|no\s+one\s+ever|"
    r"are\s+not|is\s+not|aren'?t|was\s+not|were\s+not|"
    r"refuse\w*|prohibit\w*|forbid\w*|"
    r"not\s+authori[sz]ed|unauthori[sz]ed|not\s+affiliated"
    r")\b",
    re.IGNORECASE,
)

# Weak denial: negates a noun phrase only.  "no experience needed" must not
# blanket-protect an unrelated clause, so these need the re-assertion check.
_WEAK_DENIAL_RE = re.compile(
    r"\b(?:no|not|without|zero|nil|free|never\s+be|excludes?|excluding)\b",
    re.IGNORECASE,
)

# Combined cue scan, strongest first.
_NEGATION_CUE_RE = re.compile(
    rf"(?:{_STRONG_DENIAL_RE.pattern})|(?:{_WEAK_DENIAL_RE.pattern})",
    re.IGNORECASE,
)


def _cue_is_strong(cue_text: str) -> bool:
    """``True`` when the matched cue is an absolute refusal."""
    return _STRONG_DENIAL_RE.fullmatch(cue_text.strip()) is not None


# ---------------------------------------------------------------------------
# Re-assertion / directive markers
# ---------------------------------------------------------------------------

# "We never ask you to pay a registration fee" — the payment verb here is the
# *complement* of the denial, not a fresh demand.
_ASK_OF_CANDIDATE_RE = re.compile(
    r"\b(?:ask|asks|asking|require|requires|required|request|requests|requesting|"
    r"instruct|instructs|instructing|tell|tells|telling|advise|advises|advising|"
    r"direct|directs|expect|expects|expecting|want|wants|need|needs|seek|seeks|"
    r"permit|permits|allow|allows|authori[sz]e|authori[sz]es)\w*\s+"
    r"(?:you|your|the\s+candidate|the\s+applicant|applicants?|us|anyone|any\s+person)\s+"
    r"(?:to\s+|for\s+|any\s+)?",
    re.IGNORECASE,
)

# An explicit demand or affirmative employer commitment inside the clause.
_DEMAND_REASSERTION_RE = re.compile(
    r"\b(?:"
    r"pay|pays|paid|paying|send|sends|sent|sending|transfer|transfers|transferred|"
    r"remit|remits|remittance|deposit|deposits|recharge|recharges|recharging|"
    r"top\s*up|wire|encash|encashed|"
    r"issue|issues|issued|mail|mails|mailed|courier|couriers|dispatch|dispatches|"
    r"release|releases|reimburse|reimburses"
    r")\b",
    re.IGNORECASE,
)

# Directives aimed at the reader.  These are the "instructional action keywords"
# that make a clause *active* no matter what negation surrounds it: the speaker
# is ordering the candidate to do something.
_DIRECTIVE_RE = re.compile(
    r"(?:"
    # "you must pay", "you are required to send", "the candidate shall deposit"
    r"\b(?:you|the\s+candidate|the\s+applicant|applicant)\s+"
    r"(?:must|should|shall|need\s+to|have\s+to|are\s+(?:required|expected|obligated|"
    r"asked|liable)\s+to|will\s+have\s+to|will\s+be\s+sent|will\s+receive)\b"
    # "please pay", "kindly send", "download the app", "add our HR team"
    r"|\b(?:please|kindly|go\s+ahead\s+and)\s+"
    r"(?:pay|send|transfer|deposit|remit|submit|recharge|top\s*up|share|provide|"
    r"download|install|add|sign\s+up|register)\b"
    r"|\b(?:download|install|add)\s+(?:the\s+|our\s+|this\s+)?"
    r"(?:app|application|software|username|user\s+name|id|me|number)\b"
    # "message us within 24 hours"
    r"|\b(?:message|call|contact|write|reply|respond|reach\s+out|sign\s+up)\s+"
    r"(?:us|me|on|within)\b[^.]{0,24}?\bwithin\s+\d+\s*"
    r"(?:hour|hr|minute|min|day)s?\b"
    # "we will mail you a check", "our HR will send the deposit request"
    r"|\b(?:we|our\s+(?:hr|team|recruiter|company)|the\s+company|management)\s+"
    r"(?:will|shall|would|must|is\s+going\s+to|are\s+going\s+to)\s+"
    r"(?:mail|send|issue|release|dispatch|deliver|courier|wire|transfer|pay|give|"
    r"provide|share|upload|request)\b"
    # "payment is mandatory", "a deposit is required to proceed"
    r"|\b(?:payment|deposit|fee|charge|amount|advance)\s+"
    r"(?:is|are)\s+(?:mandatory|required|compulsory|non[-\s]?negotiable)\b"
    r")",
    re.IGNORECASE,
)

# A whole clause framed as a public anti-scam warning.  A denial inside such a
# clause is unambiguously protective.
_DISCLAIMER_FRAME_RE = re.compile(
    r"\b(?:fraud|fraudulent|fraudsters?|scam|scammer|scammers|phishing|phish|"
    r"impersonat\w*|impersonators?|spoof\w*|beware|caution|warning|alert|"
    r"unscrupulous|misleading|unauthori[sz]ed|not\s+affiliated|"
    r"report\s+it|cyber\s*crime|it\s+is\s+to\s+be\s+noted|please\s+note|"
    r"kindly\s+note|take\s+note|be\s+advised)\b",
    re.IGNORECASE,
)

# Third-party attribution — the clause describes what *someone else* does, so
# the mechanic is being reported, not performed.  A disclaimer frame alone is
# not enough ("Warning: fraudsters ask for fees") because the third party is
# what makes the warning protective rather than accusatory.
_THIRD_PARTY_RE = re.compile(
    r"\b(?:fraudsters?|scammers?|scam\s?artists?|phishers?|"
    r"impersonators?|fraudulent\s+(?:callers?|agents?|recruiters?|persons?|parties?)|"
    r"anyone\s+who|anyone\s+that|anyone|any\s+person\s+who|people\s+who|"
    r"those\s+who|persons?\s+who|third\s+parties?|others\s+who)\b",
    re.IGNORECASE,
)

# Characters scanned *after* a match looking for a post-posed denial
# ("financial checks **are never issued**").
_POSTPOSED_WINDOW = 48


# ---------------------------------------------------------------------------
# Clause bounds
# ---------------------------------------------------------------------------

def _sentence_bounds(text: str, index: int, bounds: list[int] | None = None) -> tuple[int, int]:
    """Return the ``[start, end)`` sentence containing ``index``."""
    return _bounds_around(bounds if bounds is not None else _sentence_boundaries(text), index)


def _clause_bounds(
    text: str, index: int, bounds: list[int] | None = None
) -> tuple[int, int]:
    """Return the clause containing ``index``, split at contrastive connectives."""
    sent_start, sent_end = _sentence_bounds(text, index, bounds)

    start = sent_start
    for boundary in _CONTRASTIVE_RE.finditer(text, sent_start, index):
        start = boundary.end()

    end = sent_end
    boundary = _CONTRASTIVE_RE.search(text, index, sent_end)
    if boundary:
        end = boundary.start()

    return start, end


def find_negation_cue(
    text: str, start: int, end: int, bounds: list[int] | None = None
) -> tuple[str, str] | None:
    """Return ``(cue_text, governed_scope)`` for the denial governing a match.

    ``None`` when the clause containing ``[start, end)`` carries no denial.
    The scope is the text between the negation cue and the match — everything a
    reader would attach to the denial.
    """
    clause_start, clause_end = _clause_bounds(text, start, bounds)
    prefix = text[clause_start:start]

    cues = list(_NEGATION_CUE_RE.finditer(prefix))
    if cues:
        cue = cues[-1]
        return cue.group(0), prefix[cue.end():]

    # Post-posed denial: "checks are never issued by us".
    tail = text[end:clause_end]
    window = tail[:_POSTPOSED_WINDOW]
    postposed = _NEGATION_CUE_RE.search(window)
    if postposed:
        return postposed.group(0), window[:postposed.start()]

    return None


# ---------------------------------------------------------------------------
# Active vs passive decision
# ---------------------------------------------------------------------------

def _scope_reasserts_demand(scope: str) -> bool:
    """``True`` when ``scope`` re-opens a demand the denial appeared to close.

    Handles two shapes:

    * a bare demand — ``"no hidden charges, just pay the registration fee"``
    * a complement of a request — ``"no requirement to pay a fee"`` (passive)
    """
    demand = _DEMAND_REASSERTION_RE.search(scope)
    if not demand:
        return False
    ask = _ASK_OF_CANDIDATE_RE.search(scope)
    if ask and ask.end() <= demand.start():
        # "ask you to pay" — the verb is governed by the denial itself.
        return False
    return True


def is_passive_reference(text: str, start: int, end: int) -> bool:
    """``True`` when ``text[start:end)`` is a denied or warned-about reference.

    Args:
        text: The full text the match was found in.
        start: Match start offset.
        end: Match end offset.

    Returns:
        ``True`` when the clause *denies* the mechanic (passive protective
        warning), ``False`` when it *instructs or performs* it (active fraud
        mechanic).
    """
    if not text or start < 0 or end > len(text) or start >= end:
        return False

    bounds = _sentence_boundaries(text)
    clause_start, clause_end = _clause_bounds(text, start, bounds)
    clause = text[clause_start:clause_end]

    cue = find_negation_cue(text, start, end, bounds)

    # A public anti-scam warning is protective on its own, without an explicit
    # negation cue: "Beware of fraudsters who ask for registration fees."
    # Requires third-party attribution (the mechanic belongs to someone else)
    # and no directive aimed at the reader — otherwise an attacker could hide a
    # demand inside a warning clause.
    if (
        _DISCLAIMER_FRAME_RE.search(clause)
        and _THIRD_PARTY_RE.search(clause)
        and not _DIRECTIVE_RE.search(clause)
    ):
        return True

    if cue is None:
        return False

    cue_text, scope = cue

    # A directive aimed at the reader beats any surrounding denial.
    # Scope first (a "please pay" after the denial), then the whole clause
    # (a "you must deposit ₹5000" anywhere in it).
    if _DIRECTIVE_RE.search(scope) or _DIRECTIVE_RE.search(clause):
        return False

    if _DISCLAIMER_FRAME_RE.search(clause):
        return True

    if _cue_is_strong(cue_text):
        return True

    return not _scope_reasserts_demand(scope)


# ---------------------------------------------------------------------------
# Convenience helpers used by the analyzers
# ---------------------------------------------------------------------------

def iter_active_matches(
    text: str, pattern: re.Pattern[str]
) -> Iterator[re.Match[str]]:
    """Yield every match of ``pattern`` that is *not* a passive reference."""
    if not text:
        return
    for match in pattern.finditer(text):
        if not is_passive_reference(text, match.start(), match.end()):
            yield match


def first_active_match(text: str, pattern: re.Pattern[str]) -> re.Match[str] | None:
    """Return the first non-passive match of ``pattern``, or ``None``."""
    for match in iter_active_matches(text, pattern):
        return match
    return None


def has_active_match(text: str, pattern: re.Pattern[str]) -> bool:
    """``True`` when ``pattern`` matches outside a denied clause."""
    return first_active_match(text, pattern) is not None