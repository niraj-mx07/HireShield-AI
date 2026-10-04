"""Message & Transcript Analysis Engine.

Scans pasted chat transcripts, SMS threads and e-mail bodies for conversational
phishing traps.  Two rules live here:

Rule 1 — **Zero-tolerance chat-redirection gate.**  Corporate recruitment being
handled over a personal or anonymous chat network (Telegram, Signal, WhatsApp,
Discord, a bare ``@handle`` …) when the candidate is instructed to download an
app or contact a manager on that network for an interview / onboarding
briefing is treated as a definitive security violation.  The caller emits a
:class:`~app.models.schemas.RiskFactor` carrying
:data:`~app.models.schemas.CHAT_REDIRECT_GATE_SOURCE`, which the risk engine
turns into a hard score floor (92+) plus a forced ``DON'T APPLY`` verdict.

Rule 3 — **Enterprise video-platform bypass.**  The gate is *not* raised when
the text explicitly references an enterprise video platform (Microsoft Teams,
Zoom, Webex) alongside a corporate e-mail invitation domain — legitimate
interviews routinely mention such apps.

Rule 4 — **Negation scope.**  A platform named inside a *denied* clause is not a
redirection.  *"Infosys never conducts interviews over anonymous chat
applications such as WhatsApp"* is an anti-fraud notice; raising the gate on it
forced a 92+ score and a ``DON'T APPLY`` verdict against a real employer.  Every
platform mention is therefore scoped through
:mod:`app.services.negation_scope` before the gate is considered.

Nothing in this module asserts fraud as fact; it returns *indicators* only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services import negation_scope

# ---------------------------------------------------------------------------
# Rule 1 — personal / anonymous chat-network detection
# ---------------------------------------------------------------------------

# Platform keywords: named networks, short links, and bare social @handles.
_CHAT_PLATFORM_RE = re.compile(
    r"\b(?:telegram|whatsapp|signal|viber|imo|discord|snapchat|wechat|kik)\b"
    r"|(?:https?://)?(?:t\.me|wa\.me|chat\.whatsapp\.com|signal\.me|discord\.gg)"
    r"|(?<![\w.])@[a-zA-Z0-9_]{4,}\b",
    re.IGNORECASE,
)

# Bare ``@handles`` imply "contact us here"; other platforms need an explicit
# contact / download instruction nearby.
_HANDLE_RE = re.compile(r"(?<![\w.])@[a-zA-Z0-9_]{4,}\b")

# Verbs that instruct the candidate to reach out or switch channels.
_INSTRUCTION_RE = re.compile(
    r"\b(?:download\w*|install\w*|contact\w*|message\w*|dm|ping|reach(?:\s+out)?|"
    r"chat|talk|text|call|join|connect|apply|register|speak|whatsapp|"
    r"add\s+me|move\s+(?:the|our|this)|shift\s+(?:the|our|this))\b",
    re.IGNORECASE,
)

# "… on telegram" / "… via signal" — the preposition that introduces the
# platform.  Matched against the text immediately *preceding* the mention.
_DIRECTIONAL_PREPOSITION_RE = re.compile(
    r"\b(?:on|via|through|over|using|by)\s+(?:the\s+|our\s+|this\s+)?$",
    re.IGNORECASE,
)

# "telegram app / signal channel / whatsapp group …" — the noun that follows.
_DIRECTIONAL_SUFFIX_RE = re.compile(
    r"^\s+(?:app|channel|group|chat|account|id|handle|number)\b",
    re.IGNORECASE,
)

# Recruitment / onboarding framing that makes a channel switch meaningful.
_RECRUIT_CONTEXT_RE = re.compile(
    r"\b(?:interview\w*|onboard\w*|briefing|hiring|recruit\w*|selection|"
    r"shortlist\w*|screening|offer|joining|hr|manager|supervisor|panel|"
    r"candidate\w*|application|role|position|job|assessment)\b",
    re.IGNORECASE,
)

# How far (in characters) an instruction may sit from the platform mention.
_INSTRUCTION_WINDOW = 160
_DIRECTIONAL_WINDOW = 40

# ---------------------------------------------------------------------------
# Rule 3 — enterprise video-platform + corporate invitation e-mail bypass
# ---------------------------------------------------------------------------

_ENTERPRISE_VIDEO_RE = re.compile(
    r"\b(?:microsoft\s+teams|ms\s+teams|teams\s+(?:meeting|call|invite|invitation|"
    r"interview|link)|zoom|webex|cisco\s+webex)\b",
    re.IGNORECASE,
)

# Free / consumer webmail providers — an address here is *not* a corporate
# invitation domain.
_PERSONAL_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.co.in",
        "ymail.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "msn.com",
        "icloud.com",
        "me.com",
        "mac.com",
        "proton.me",
        "protonmail.com",
        "aol.com",
        "mail.com",
        "zoho.com",
        "zohomail.com",
        "yandex.com",
        "gmx.com",
        "fastmail.com",
        "tutanota.com",
        "tutamail.com",
        "rediffmail.com",
        "aim.com",
        "inbox.com",
    }
)

_EMAIL_RE = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@([a-zA-Z0-9][a-zA-Z0-9.\-]*\.[a-zA-Z]{2,})\b"
)

# How much context to quote as evidence around a platform mention.
_EVIDENCE_WINDOW = 140


@dataclass(frozen=True)
class ChatRedirectionHit:
    """A confirmed Rule 1 chat-redirection candidate."""

    platform: str
    evidence: str



def _snippet(text: str, start: int, end: int) -> str:
    """Quote ``text`` around ``[start, end)`` trimmed to word boundaries."""
    lo = max(0, start - _EVIDENCE_WINDOW)
    hi = min(len(text), end + _EVIDENCE_WINDOW)
    snippet = " ".join(text[lo:hi].split())
    if lo > 0:
        snippet = "…" + snippet
    if hi < len(text):
        snippet += "…"
    return snippet


def has_enterprise_video_invitation(text: str) -> bool:
    """Rule 3 — enterprise video platform *and* corporate invitation e-mail.

    Returns ``True`` only when the text explicitly references Microsoft Teams /
    Zoom / Webex **and** contains an e-mail address on a non-consumer domain.
    """
    if not text:
        return False
    if not _ENTERPRISE_VIDEO_RE.search(text):
        return False
    for match in _EMAIL_RE.finditer(text):
        if match.group(1).lower().removeprefix("www.") not in _PERSONAL_EMAIL_DOMAINS:
            return True
    return False


def _instruction_near(text: str, match: re.Match[str]) -> bool:
    """True when an instruction verb or directional link sits near the match."""
    window_lo = max(0, match.start() - _INSTRUCTION_WINDOW)
    window_hi = min(len(text), match.end() + _INSTRUCTION_WINDOW)
    if _INSTRUCTION_RE.search(text[window_lo:window_hi]):
        return True

    # "… will be conducted over Signal" / "… on the Telegram".
    prefix = text[max(0, match.start() - _DIRECTIONAL_WINDOW):match.start()]
    if _DIRECTIONAL_PREPOSITION_RE.search(prefix):
        return True

    # "… Signal channel for your interview".
    suffix = text[match.end():match.end() + _DIRECTIONAL_WINDOW]
    return bool(_DIRECTIONAL_SUFFIX_RE.search(suffix))


def detect_chat_redirection(text: str | None) -> ChatRedirectionHit | None:
    """Rule 1 + Rule 3 — detect a chat-network redirection of the hiring process.

    Args:
        text: Full message / transcript payload (all input fields concatenated).

    Returns:
        A :class:`ChatRedirectionHit` when the candidate was pushed onto a
        personal or anonymous chat network for an interview or onboarding
        briefing and no enterprise-video bypass applies; otherwise ``None``.
    """
    if not text or not text.strip():
        return None

    # Rule 3 — legitimate enterprise video interviews bypass the gate.
    if has_enterprise_video_invitation(text):
        return None

    # The switch must be framed by hiring / onboarding context.
    if _RECRUIT_CONTEXT_RE.search(text) is None:
        return None

    # Check every platform mention: a hit on any of them raises the gate.
    # A bare @handle *is* the contact instruction; other platforms need an
    # explicit instruction or a directional link ("on telegram", "via signal").
    for platform_match in _CHAT_PLATFORM_RE.finditer(text):
        # Rule 4 — skip platform names sitting inside a denied clause.
        if negation_scope.is_passive_reference(
            text, platform_match.start(), platform_match.end()
        ):
            continue
        is_handle = bool(_HANDLE_RE.fullmatch(platform_match.group(0)))
        if is_handle or _instruction_near(text, platform_match):
            return ChatRedirectionHit(
                platform=platform_match.group(0),
                evidence=_snippet(text, platform_match.start(), platform_match.end()),
            )

    return None
