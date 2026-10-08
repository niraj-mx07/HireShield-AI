"""Domain-specific Feature Extractor for Job Scam Detection.

Extracts engineered linguistic, structural, and heuristic risk signals from job postings.
Compatible with Scikit-Learn's Transformer API (`BaseEstimator`, `TransformerMixin`).

v2 additions (backward compatible — existing features unchanged, new ones appended):
  - has_salary_lakh_crore       : inflated INR salary promises
  - has_internship_scam_trope   : common internship fraud patterns
  - has_social_media_contact    : Instagram/Twitter/LinkedIn DM recruitment
  - has_advance_payment         : advance-fee / refundable deposit mentions
  - has_guaranteed_job          : "guaranteed placement/selection" claims
  - has_no_experience_education : all-inclusive "no experience" claims
  - has_currency_amount         : specific rupee/dollar amounts in text
  - text_short                  : very short post (< 100 words) — often fake
  - text_very_long              : extremely long post (> 2000 words) — some fakes
  - special_char_ratio          : ratio of special chars (asterisks, pipes, etc.)
"""

from __future__ import annotations

import re
from typing import Any, List, Sequence

import numpy as np

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    pd = None
    _HAS_PANDAS = False

from sklearn.base import BaseEstimator, TransformerMixin


# ---------------------------------------------------------------------------
# Compiled Regex Signatures (original — unchanged for backward compatibility)
# ---------------------------------------------------------------------------
RE_WHATSAPP_TELEGRAM = re.compile(
    r"\b(whatsapp|wa\.me|telegram|t\.me|signal|imo|viber|contact on whatsapp|dm on telegram)\b",
    re.IGNORECASE,
)
RE_FEE_MENTION = re.compile(
    r"\b(registration fee|security deposit|processing fee|processing charge|"
    r"refundable deposit|refundable amount|training fee|training charge|"
    r"onboarding fee|laptop deposit|gate pass fee|medical fee|uniform fee|"
    r"documentation charge)\b",
    re.IGNORECASE,
)
RE_MONEY_PROMISE = re.compile(
    r"\b(daily payout|daily income|earn \$\s*\d+|earn rs\.?\s*\d+|"
    r"earn \d{3,6}\s*(per|daily|weekly|a day)|guaranteed income|"
    r"high return|instant payout|weekly payout)\b",
    re.IGNORECASE,
)
RE_SUSPICIOUS_CONTRACT = re.compile(
    r"\b(original certificate|original documents submission|submit original|"
    r"service bond|bond agreement|blank cheque|cheque submission|"
    r"penalty clause|withholding salary)\b",
    re.IGNORECASE,
)
RE_EXTERNAL_EMAIL = re.compile(
    r"@[a-zA-Z0-9._%+-]*(gmail|yahoo|hotmail|outlook|rediffmail|ymail|protonmail|aol)\.com\b",
    re.IGNORECASE,
)
RE_PHONE_NUMBER = re.compile(
    r"(\+?91[-.\ s]?)?[6-9]\d{9}|\b\d{3}[-.\ s]\d{3}[-.\ s]\d{4}\b",
    re.IGNORECASE,
)
RE_URGENCY = re.compile(
    r"\b(urgent requirement|immediate joining|spot offer|direct selection|"
    r"limited vacancies|hurry up|apply immediately|walk-in direct offer|"
    r"hiring urgently|openings today)\b",
    re.IGNORECASE,
)
RE_LOW_BARRIER_TROPE = re.compile(
    r"\b(no interview|no experience required|any degree|10th pass|12th pass|"
    r"data entry|form filling|sms sending|typing job|copy paste|ad clicking|"
    r"work 1-2 hours|simple online work|part time work from home)\b",
    re.IGNORECASE,
)
RE_PAYMENT_WALLET = re.compile(
    r"\b(gpay|google pay|phonepe|paytm|upi id|usdt|crypto|bitcoin|"
    r"recharge task|telegram task)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# v2: Additional Scam-Specific Signals
# ---------------------------------------------------------------------------
RE_SALARY_LAKH_CRORE = re.compile(
    r"\b(\d+\s*(lakh|lac|crore|cr)\s*(per\s*(month|annum|year))?|"
    r"ctc\s*\d+\s*(lakh|lac)|package\s*\d+\s*(lakh|lac))\b",
    re.IGNORECASE,
)
RE_INTERNSHIP_SCAM = re.compile(
    r"\b(internship fee|stipend guaranteed|earn while intern|"
    r"paid internship guaranteed|internship certificate guaranteed|"
    r"free certificate|certificate after payment|internship without work)\b",
    re.IGNORECASE,
)
RE_SOCIAL_MEDIA_CONTACT = re.compile(
    r"\b(dm (us|me) on instagram|contact on instagram|"
    r"message on linkedin|apply via instagram|dm for details|"
    r"reach out on twitter|contact via facebook)\b",
    re.IGNORECASE,
)
RE_ADVANCE_PAYMENT = re.compile(
    r"\b(advance payment|pay first|pay.*to get.*job|"
    r"refundable after joining|send money|transfer.*amount|"
    r"pay.*before joining|deposit.*before|initial payment)\b",
    re.IGNORECASE,
)
RE_GUARANTEED_JOB = re.compile(
    r"\b(guaranteed (placement|selection|offer|salary|job|income|hiring)|"
    r"100\s*%\s*(placement|selection|job|hiring)|assured (job|income|placement))\b",
    re.IGNORECASE,
)
RE_NO_EXP_EDU = re.compile(
    r"\b(no experience needed|no qualification required|"
    r"all are eligible|freshers eligible|anyone can apply|"
    r"no skills required|open to all|no educational requirement)\b",
    re.IGNORECASE,
)
RE_CURRENCY_AMOUNT = re.compile(
    r"(?:₹|rs\.?|inr|usd|\$)\s*\d[\d,]*|\b\d[\d,]*\s*(?:₹|rs\.?|inr|usd)",
    re.IGNORECASE,
)
RE_SPECIAL_CHARS = re.compile(r"[*|#@!$%^&+=~`<>{}\\]")


class JobPostFeatureExtractor(BaseEstimator, TransformerMixin):
    """Extracts dense engineered feature vectors from job post text.

    Feature list is append-only (new features added after index 14) to
    maintain backward compatibility with existing saved models that use
    MaxAbsScaler fitted on 15 features.

    NOTE: If you change the feature count here, retrain the full pipeline.
    """

    def __init__(self) -> None:
        self.feature_names_: List[str] = [
            # --- Original 15 features (unchanged) ---
            "log_char_len",             # 0
            "log_word_len",             # 1
            "uppercase_ratio",          # 2
            "digit_ratio",              # 3
            "exclamation_density",      # 4
            "question_density",         # 5
            "has_whatsapp_telegram",    # 6
            "has_fee_mention",          # 7
            "has_money_promise",        # 8
            "has_suspicious_contract",  # 9
            "has_external_email",       # 10
            "has_phone_number",         # 11
            "has_urgency",              # 12
            "has_low_barrier_trope",    # 13
            "has_payment_wallet",       # 14
            # --- v2 extended features ---
            "has_salary_lakh_crore",    # 15
            "has_internship_scam",      # 16
            "has_social_media_contact", # 17
            "has_advance_payment",      # 18
            "has_guaranteed_job",       # 19
            "has_no_exp_edu",           # 20
            "has_currency_amount",      # 21
            "is_text_very_short",       # 22 — <100 words
            "is_text_very_long",        # 23 — >2000 words
            "special_char_ratio",       # 24
        ]

    def fit(self, X: Any, y: Any = None) -> "JobPostFeatureExtractor":
        """Stateless — nothing to fit."""
        return self

    def transform(self, X: "Sequence[str] | pd.Series | np.ndarray") -> np.ndarray:
        """Extract structured features from an iterable of job posting texts.

        Args:
            X: Iterable of raw strings or pandas Series.

        Returns:
            2D numpy array of shape (n_samples, n_features).
        """
        if _HAS_PANDAS and isinstance(X, pd.Series):
            texts = X.fillna("").astype(str).tolist()
        elif isinstance(X, np.ndarray):
            texts = [str(x) if x is not None else "" for x in X.ravel()]
        else:
            texts = [str(x) if x is not None else "" for x in X]

        n_samples  = len(texts)
        n_features = len(self.feature_names_)
        features   = np.zeros((n_samples, n_features), dtype=np.float32)

        for i, text in enumerate(texts):
            text_len = len(text)
            words    = text.split()
            word_len = len(words)

            # --- Original features (0-14, unchanged) ---
            features[i, 0] = np.log1p(text_len)
            features[i, 1] = np.log1p(word_len)
            upper_count = sum(1 for c in text if c.isupper())
            features[i, 2] = upper_count / (text_len + 1e-5)
            digit_count = sum(1 for c in text if c.isdigit())
            features[i, 3] = digit_count / (text_len + 1e-5)
            features[i, 4] = (text.count("!") / (text_len + 1e-5)) * 1000.0
            features[i, 5] = (text.count("?") / (text_len + 1e-5)) * 1000.0
            features[i, 6]  = 1.0 if RE_WHATSAPP_TELEGRAM.search(text) else 0.0
            features[i, 7]  = 1.0 if RE_FEE_MENTION.search(text) else 0.0
            features[i, 8]  = 1.0 if RE_MONEY_PROMISE.search(text) else 0.0
            features[i, 9]  = 1.0 if RE_SUSPICIOUS_CONTRACT.search(text) else 0.0
            features[i, 10] = 1.0 if RE_EXTERNAL_EMAIL.search(text) else 0.0
            features[i, 11] = 1.0 if RE_PHONE_NUMBER.search(text) else 0.0
            features[i, 12] = 1.0 if RE_URGENCY.search(text) else 0.0
            features[i, 13] = 1.0 if RE_LOW_BARRIER_TROPE.search(text) else 0.0
            features[i, 14] = 1.0 if RE_PAYMENT_WALLET.search(text) else 0.0

            # --- v2 extended features (15-24) ---
            features[i, 15] = 1.0 if RE_SALARY_LAKH_CRORE.search(text) else 0.0
            features[i, 16] = 1.0 if RE_INTERNSHIP_SCAM.search(text) else 0.0
            features[i, 17] = 1.0 if RE_SOCIAL_MEDIA_CONTACT.search(text) else 0.0
            features[i, 18] = 1.0 if RE_ADVANCE_PAYMENT.search(text) else 0.0
            features[i, 19] = 1.0 if RE_GUARANTEED_JOB.search(text) else 0.0
            features[i, 20] = 1.0 if RE_NO_EXP_EDU.search(text) else 0.0
            features[i, 21] = 1.0 if RE_CURRENCY_AMOUNT.search(text) else 0.0
            features[i, 22] = 1.0 if word_len < 100 else 0.0
            features[i, 23] = 1.0 if word_len > 2000 else 0.0
            special_count = len(RE_SPECIAL_CHARS.findall(text))
            features[i, 24] = special_count / (text_len + 1e-5)

        return features

    def get_feature_names_out(self, input_features: Any = None) -> List[str]:
        return list(self.feature_names_)
