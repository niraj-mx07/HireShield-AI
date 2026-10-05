"""Domain-specific Feature Extractor for Job Scam Detection.

Extracts engineered linguistic, structural, and heuristic risk signals from job postings.
Compatible with Scikit-Learn's Transformer API (`BaseEstimator`, `TransformerMixin`).
Optimized with linear-time bounded regexes to ensure instantaneous extraction across large datasets.
"""

from __future__ import annotations

import re
from typing import Any, List, Sequence, Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


# ---------------------------------------------------------------------------
# Linear-Time Compiled Regex Signatures (Zero Backtracking)
# ---------------------------------------------------------------------------
RE_WHATSAPP_TELEGRAM = re.compile(
    r"\b(whatsapp|wa\.me|telegram|t\.me|signal|imo|viber|contact on whatsapp|dm on telegram)\b",
    re.IGNORECASE,
)
RE_FEE_MENTION = re.compile(
    r"\b(registration fee|security deposit|caution deposit|processing fee|processing charge|"
    r"refundable deposit|refundable amount|training fee|training charge|onboarding fee|laptop deposit|"
    r"gate pass fee|medical fee|uniform fee|uniform charge|documentation charge|rfid badge fee|"
    r"courier charge|shipping insurance fee|dispatch charge)\b",
    re.IGNORECASE,
)
RE_MONEY_PROMISE = re.compile(
    r"\b(daily payout|daily income|guaranteed income|high return|instant payout|weekly payout|"
    r"earn \$\s*\d+|earn rs\.?\s*\d+)\b",
    re.IGNORECASE,
)
RE_SUSPICIOUS_CONTRACT = re.compile(
    r"\b(original certificate|original documents submission|submit original|service bond|bond agreement|"
    r"blank cheque|cheque submission|penalty clause|withholding salary|salary withheld)\b",
    re.IGNORECASE,
)
RE_EXTERNAL_EMAIL = re.compile(
    r"@(gmail|yahoo|hotmail|outlook|rediffmail|ymail|protonmail|aol)\.com\b",
    re.IGNORECASE,
)
RE_PHONE_NUMBER = re.compile(
    r"\b(?:\+?91[-.\s]?)?[6-9]\d{9}\b|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
    re.IGNORECASE,
)
RE_URGENCY = re.compile(
    r"\b(urgent requirement|immediate joining|spot offer|direct selection|limited vacancies|hurry up|"
    r"apply immediately|walk-in direct offer|hiring urgently|openings today)\b",
    re.IGNORECASE,
)
RE_LOW_BARRIER_TROPE = re.compile(
    r"\b(no interview|no experience required|any degree|10th pass|12th pass|data entry|form filling|"
    r"sms sending|typing job|copy paste|ad clicking|work 1-2 hours|simple online work|"
    r"part time work from home|software utility key|portal activation charge)\b",
    re.IGNORECASE,
)
RE_PAYMENT_WALLET = re.compile(
    r"\b(gpay|google pay|phonepe|paytm|bhim|qr code|upi id|usdt|crypto|bitcoin|recharge task|telegram task)\b",
    re.IGNORECASE,
)
RE_CHECK_EQUIPMENT_SCAM = re.compile(
    r"\b(cashier'?s?\s*check|reimbursement check|approved vendor|certified vendor|mobile check deposit|"
    r"certified equipment vendor|home office equipment check|vendor portal via zelle)\b",
    re.IGNORECASE,
)
RE_TASK_RATING_SCAM = re.compile(
    r"\b(like and subscribe|youtube task|google maps review|rating task|prepaid task|recharge wallet|"
    r"task commission|order rating task|crypto arbitrage|quantitative task|commission tiers)\b",
    re.IGNORECASE,
)
RE_UPI_HANDLE = re.compile(
    r"\b[a-zA-Z0-9.\-_]{2,32}@(okaxis|okhdfcbank|okicici|oksbi|paytm|ybl|ibl|axl|upi)\b",
    re.IGNORECASE,
)
RE_CRYPTO_TRAP = re.compile(
    r"\b(trc20|erc20|usdt|trust wallet|metamask|crypto wallet|binance vip|crypto voucher)\b",
    re.IGNORECASE,
)
RE_FREE_HOSTING_SHORTENER = re.compile(
    r"\b(firebaseapp\.com|web\.app|glitch\.me|blogspot\.com|wixsite\.com|weebly\.com|bit\.ly|tinyurl\.com|t\.ly)\b",
    re.IGNORECASE,
)
RE_LEGITIMATE_SIGNALS = re.compile(
    r"\b(equal opportunity employer|affirmative action|never request payment|anti[- ]scam notice|"
    r"provident fund|401\(k\)|health insurance|paid time off|esop|equity options|zero-fee recruitment)\b",
    re.IGNORECASE,
)


class JobPostFeatureExtractor(BaseEstimator, TransformerMixin):
    """Extracts dense engineered feature vectors from job post text."""

    def __init__(self) -> None:
        self.feature_names_: List[str] = [
            "log_char_len",
            "log_word_len",
            "uppercase_ratio",
            "digit_ratio",
            "exclamation_density",
            "question_density",
            "has_whatsapp_telegram",
            "has_fee_mention",
            "has_money_promise",
            "has_suspicious_contract",
            "has_external_email",
            "has_phone_number",
            "has_urgency",
            "has_low_barrier_trope",
            "has_payment_wallet",
            "has_check_reimbursement",
            "has_task_investment",
            "has_upi_handle",
            "has_crypto_trap",
            "has_free_hosting_shortener",
            "has_legitimate_signals",
        ]

    def fit(self, X: Any, y: Any = None) -> JobPostFeatureExtractor:
        """Fit method (stateless)."""
        return self

    def transform(self, X: Sequence[str] | pd.Series | np.ndarray) -> np.ndarray:
        """Extract structured features from an iterable of job posting texts."""
        if isinstance(X, pd.Series):
            texts = X.fillna("").astype(str).tolist()
        elif isinstance(X, np.ndarray):
            texts = [str(x) if x is not None else "" for x in X.ravel()]
        else:
            texts = [str(x) if x is not None else "" for x in X]

        n_samples = len(texts)
        n_features = len(self.feature_names_)
        features = np.zeros((n_samples, n_features), dtype=np.float32)

        for i, text in enumerate(texts):
            text_len = len(text)
            words = text.split()
            word_len = len(words)

            # 0. log char length
            features[i, 0] = np.log1p(text_len)
            # 1. log word length
            features[i, 1] = np.log1p(word_len)
            # 2. uppercase ratio
            upper_count = sum(map(str.isupper, text))
            features[i, 2] = upper_count / (text_len + 1e-5)
            # 3. digit ratio
            digit_count = sum(map(str.isdigit, text))
            features[i, 3] = digit_count / (text_len + 1e-5)
            # 4. exclamation density (per 1000 chars)
            features[i, 4] = (text.count("!") / (text_len + 1e-5)) * 1000.0
            # 5. question density (per 1000 chars)
            features[i, 5] = (text.count("?") / (text_len + 1e-5)) * 1000.0

            # Binary Parameter Signals
            features[i, 6] = 1.0 if RE_WHATSAPP_TELEGRAM.search(text) else 0.0
            features[i, 7] = 1.0 if RE_FEE_MENTION.search(text) else 0.0
            features[i, 8] = 1.0 if RE_MONEY_PROMISE.search(text) else 0.0
            features[i, 9] = 1.0 if RE_SUSPICIOUS_CONTRACT.search(text) else 0.0
            features[i, 10] = 1.0 if RE_EXTERNAL_EMAIL.search(text) else 0.0
            features[i, 11] = 1.0 if RE_PHONE_NUMBER.search(text) else 0.0
            features[i, 12] = 1.0 if RE_URGENCY.search(text) else 0.0
            features[i, 13] = 1.0 if RE_LOW_BARRIER_TROPE.search(text) else 0.0
            features[i, 14] = 1.0 if RE_PAYMENT_WALLET.search(text) else 0.0
            features[i, 15] = 1.0 if RE_CHECK_EQUIPMENT_SCAM.search(text) else 0.0
            features[i, 16] = 1.0 if RE_TASK_RATING_SCAM.search(text) else 0.0
            features[i, 17] = 1.0 if RE_UPI_HANDLE.search(text) else 0.0
            features[i, 18] = 1.0 if RE_CRYPTO_TRAP.search(text) else 0.0
            features[i, 19] = 1.0 if RE_FREE_HOSTING_SHORTENER.search(text) else 0.0
            features[i, 20] = 1.0 if RE_LEGITIMATE_SIGNALS.search(text) else 0.0

        return features

    def explain_triggers(self, text: str) -> list[str]:
        """Return human-readable risk signals triggered in the text."""
        triggers: list[str] = []
        if RE_FEE_MENTION.search(text):
            triggers.append("Upfront registration fee or security deposit demanded")
        if RE_CHECK_EQUIPMENT_SCAM.search(text):
            triggers.append("Cashier's check equipment reimbursement overpayment trap")
        if RE_WHATSAPP_TELEGRAM.search(text):
            triggers.append("Direct recruitment conducted via WhatsApp / Telegram")
        if RE_TASK_RATING_SCAM.search(text):
            triggers.append("Prepaid task, video rating, or recharge commission trap")
        if RE_UPI_HANDLE.search(text):
            triggers.append("Personal peer-to-peer UPI VPA ID identified in listing")
        if RE_CRYPTO_TRAP.search(text):
            triggers.append("Cryptocurrency / USDT wallet payment demand")
        if RE_SUSPICIOUS_CONTRACT.search(text):
            triggers.append("Mandatory original certificates, blank cheque, or service bond penalty")
        if RE_LOW_BARRIER_TROPE.search(text):
            triggers.append("Low qualification / high payout typing or data entry trope")
        if RE_EXTERNAL_EMAIL.search(text):
            triggers.append("Free webmail address used for official hiring communications")
        return triggers

    def get_feature_names_out(self, input_features: Any = None) -> List[str]:
        return list(self.feature_names_)
