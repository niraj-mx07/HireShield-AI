"""Model wrapper module for packaging boosted ML pipelines.

Defines `BoostedModelWrapper`, which pairs TF-IDF vectorization, dense heuristic
feature extraction, feature scaling, and ensemble classification into a unified,
production-ready inference pipeline for backend and evaluation use.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack, issparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MaxAbsScaler

from ml.training.feature_extractor import JobPostFeatureExtractor


class BoostedModelWrapper:
    """Wrapper that packages the boosted pipeline for backend compatibility.

    The backend calls either:
        model.predict_proba([combined_text])
    or:
        features = vectorizer.transform([combined_text])
        model.predict_proba(features)

    This wrapper seamlessly handles both inputs, exposes .coef_ for explainability,
    and supports domain heuristic explanations.
    """
    is_boosted: bool = True

    def __init__(
        self,
        word_tfidf: TfidfVectorizer,
        feature_extractor: JobPostFeatureExtractor,
        scaler: MaxAbsScaler,
        model: Any,
        optimal_threshold: float = 0.5,
    ) -> None:
        self.word_tfidf = word_tfidf
        self.feature_extractor = feature_extractor
        self.scaler = scaler
        self.model = model
        self.optimal_threshold = optimal_threshold

    @property
    def coef_(self) -> Any:
        """Provide coef_ from underlying model for explainable n-gram attribution."""
        if hasattr(self.model, "coef_"):
            return self.model.coef_
        if hasattr(self.model, "estimators_"):
            for est in self.model.estimators_:
                if hasattr(est, "coef_"):
                    return est.coef_
        return None

    def predict(self, X_input: Any) -> np.ndarray:
        """Predict from raw text or pre-vectorized sparse matrix."""
        proba = self.predict_proba(X_input)[:, 1]
        return (proba >= self.optimal_threshold).astype(int)

    def predict_proba(self, X_input: Any) -> np.ndarray:
        """Return probability estimates [P(real), P(fraud)]."""
        if isinstance(X_input, str):
            X_input = [X_input]

        if isinstance(X_input, (list, tuple, pd.Series)) or (
            isinstance(X_input, np.ndarray) and X_input.dtype.kind in ("U", "S", "O")
        ):
            X_combined = self._build_features(X_input)
            if hasattr(self.model, "predict_proba"):
                return self.model.predict_proba(X_combined)
            preds = self.model.predict(X_combined)
            return np.column_stack([1.0 - preds, preds])

        if issparse(X_input):
            expected_dim = getattr(self.model, "n_features_in_", None)
            if expected_dim is None or X_input.shape[1] == expected_dim:
                return self.model.predict_proba(X_input)
            if expected_dim is not None and X_input.shape[1] < expected_dim:
                diff = expected_dim - X_input.shape[1]
                zero_padding = csr_matrix((X_input.shape[0], diff), dtype=np.float32)
                X_padded = hstack([X_input, zero_padding])
                return self.model.predict_proba(X_padded)

        return self.model.predict_proba(X_input)

    def _build_features(self, texts: Any) -> Any:
        """Build the full feature matrix from raw texts."""
        X_word = self.word_tfidf.transform(texts)
        X_feat = self.feature_extractor.transform(texts)
        X_feat_scaled = self.scaler.transform(X_feat)
        return hstack([X_word, csr_matrix(X_feat_scaled)])
