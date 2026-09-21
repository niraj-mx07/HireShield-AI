"""Domain-specific Feature Extractor for Job Scam Detection.

Extracts engineered linguistic, structural, and heuristic risk signals from job postings.
Compatible with Scikit-Learn's Transformer API (`BaseEstimator`, `TransformerMixin`).
"""

from __future__ import annotations

import re
from typing import Any, List, Sequence, Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


# ---------------------------------------------------------------------------
# Compiled Regex Signatures
# ---------------------------------------------------------------------------
RE_WHATSAPP_TELEGRAM = re.compile(
    r"\b(whatsapp|wa\.me|telegram|t\.me|signal|imo|viber|contact on whatsapp|dm on telegram)\b",
    re.IGNORECASE,
)
RE_FEE_MENTION = re.compile(
    r"\b(registration fee|security deposit|processing fee|processing charge|refundable deposit|refundable amount|training fee|training charge|onboarding fee|laptop deposit|gate pass fee|medical fee|uniform fee|documentation charge)\b",
    re.IGNORECASE,
)
RE_MONEY_PROMISE = re.compile(
    r"\b(daily payout|daily income|earn \$\s*\d+|earn rs\.?\s*\d+|earn \d{3,6}\s*(per|daily|weekly|a day)|guaranteed income|high return|instant payout|weekly payout)\b",
    re.IGNORECASE,
)
RE_SUSPICIOUS_CONTRACT = re.compile(
    r"\b(original certificate|original documents submission|submit original|service bond|bond agreement|blank cheque|cheque submission|penalty clause|withholding salary)\b",
    re.IGNORECASE,
)
RE_EXTERNAL_EMAIL = re.compile(
    r"@[a-zA-Z0-9._%+-]*(gmail|yahoo|hotmail|outlook|rediffmail|ymail|protonmail|aol)\.com\b",
    re.IGNORECASE,
)
RE_PHONE_NUMBER = re.compile(
    r"(\+?91[-.\s]?)?[6-9]\d{9}|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
    re.IGNORECASE,
)
RE_URGENCY = re.compile(
    r"\b(urgent requirement|immediate joining|spot offer|direct selection|limited vacancies|hurry up|apply immediately|walk-in direct offer|hiring urgently|openings today)\b",
    re.IGNORECASE,
)
RE_LOW_BARRIER_TROPE = re.compile(
    r"\b(no interview|no experience required|any degree|10th pass|12th pass|data entry|form filling|sms sending|typing job|copy paste|ad clicking|work 1-2 hours|simple online work|part time work from home)\b",
    re.IGNORECASE,
)
RE_PAYMENT_WALLET = re.compile(
    r"\b(gpay|google pay|phonepe|paytm|upi id|usdt|crypto|bitcoin|recharge task|telegram task)\b",
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
        ]

    def fit(self, X: Any, y: Any = None) -> JobPostFeatureExtractor:
        """Fit method (stateless)."""
        return self

    def transform(self, X: Sequence[str] | pd.Series | np.ndarray) -> np.ndarray:
        """Extract structured features from an iterable of job posting texts.

        Args:
            X: Iterable of raw strings or pandas Series.

        Returns:
            2D numpy array of shape (n_samples, n_features).
        """
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
            upper_count = sum(1 for c in text if c.isupper())
            features[i, 2] = upper_count / (text_len + 1e-5)
            # 3. digit ratio
            digit_count = sum(1 for c in text if c.isdigit())
            features[i, 3] = digit_count / (text_len + 1e-5)
            # 4. exclamation density (per 1000 chars)
            features[i, 4] = (text.count("!") / (text_len + 1e-5)) * 1000.0
            # 5. question density (per 1000 chars)
            features[i, 5] = (text.count("?") / (text_len + 1e-5)) * 1000.0

            # Binary Heuristic Signals
            features[i, 6] = 1.0 if RE_WHATSAPP_TELEGRAM.search(text) else 0.0
            features[i, 7] = 1.0 if RE_FEE_MENTION.search(text) else 0.0
            features[i, 8] = 1.0 if RE_MONEY_PROMISE.search(text) else 0.0
            features[i, 9] = 1.0 if RE_SUSPICIOUS_CONTRACT.search(text) else 0.0
            features[i, 10] = 1.0 if RE_EXTERNAL_EMAIL.search(text) else 0.0
            features[i, 11] = 1.0 if RE_PHONE_NUMBER.search(text) else 0.0
            features[i, 12] = 1.0 if RE_URGENCY.search(text) else 0.0
            features[i, 13] = 1.0 if RE_LOW_BARRIER_TROPE.search(text) else 0.0
            features[i, 14] = 1.0 if RE_PAYMENT_WALLET.search(text) else 0.0

        return features

    def get_feature_names_out(self, input_features: Any = None) -> List[str]:
        return list(self.feature_names_)
