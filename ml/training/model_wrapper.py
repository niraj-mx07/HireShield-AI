"""Shared model wrapper classes for HireShield-AI ML pipeline.

Defines ImprovedModelWrapper (pipeline v2) and re-exports BoostedModelWrapper
(pipeline v1) so that joblib can deserialize artifacts regardless of which
script loaded them.

Import from here in:
  - ml/training/train_improved.py  (to save)
  - ml/evaluation/evaluate.py      (to load)
  - backend job_content.py         (loaded via model_loader.py)
"""

from __future__ import annotations

from typing import Any, List

import numpy as np
from scipy.sparse import csr_matrix, hstack, issparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MaxAbsScaler

from ml.training.feature_extractor import JobPostFeatureExtractor


class ImprovedModelWrapper:
    """Pipeline wrapper for the improved model — backend compatible.

    Saves alongside tfidf_vectorizer.joblib as best_model.joblib.

    Supports two call modes used by the backend:
      1. Raw text list/Series  -> builds word TF-IDF + heuristics internally.
      2. Sparse matrix         -> passed directly to the inner classifier.

    The backend model_loader.py caches this object and job_content.py calls
    predict_proba([text]) directly (not via the sparse path).
    """
    VERSION = "improved_v2"

    def __init__(
        self,
        word_tfidf: TfidfVectorizer,
        feat_extractor: JobPostFeatureExtractor,
        scaler: MaxAbsScaler,
        model: Any,
        optimal_threshold: float = 0.5,
        word_vocab_size: int = 0,
    ) -> None:
        self.word_tfidf        = word_tfidf
        self.feat_extractor    = feat_extractor
        self.scaler            = scaler
        self.model             = model
        self.optimal_threshold = optimal_threshold
        self.word_vocab_size   = word_vocab_size
        self._set_coef()

    def _set_coef(self) -> None:
        """Forward coef_ from inner model for explainability in job_content.py."""
        m = self.model
        if hasattr(m, "coef_"):
            self.coef_ = m.coef_
        elif hasattr(m, "calibrated_classifiers_"):
            try:
                self.coef_ = m.calibrated_classifiers_[0].estimator.coef_
            except Exception:
                pass
        elif hasattr(m, "estimators_"):
            for _, est in m.estimators:
                base = est
                if hasattr(base, "calibrated_classifiers_"):
                    try:
                        base = base.calibrated_classifiers_[0].estimator
                    except Exception:
                        pass
                if hasattr(base, "coef_"):
                    self.coef_ = base.coef_
                    break

    def _build_features(self, texts: Any) -> Any:
        """Build combined word TF-IDF + heuristic feature matrix from raw text."""
        X_w = self.word_tfidf.transform(texts)
        X_h = self.feat_extractor.transform(texts)
        X_h_s = self.scaler.transform(X_h)
        return hstack([X_w, csr_matrix(X_h_s)]).tocsr()

    def predict(self, X: Any) -> np.ndarray:
        """Predict fraud class. Accepts raw text list or sparse matrix."""
        if issparse(X):
            if hasattr(self.model, "predict_proba"):
                p = self.model.predict_proba(X)[:, 1]
                return (p >= self.optimal_threshold).astype(int)
            return self.model.predict(X)
        Xc = self._build_features(X)
        if hasattr(self.model, "predict_proba"):
            p = self.model.predict_proba(Xc)[:, 1]
            return (p >= self.optimal_threshold).astype(int)
        return self.model.predict(Xc)

    def predict_proba(self, X: Any) -> np.ndarray:
        """Return [[p_real, p_fraud]] probabilities."""
        if issparse(X):
            return self.model.predict_proba(X)
        return self.model.predict_proba(self._build_features(X))

    def get_feature_names_out(self) -> List[str]:
        return list(self.word_tfidf.get_feature_names_out()) + \
               list(self.feat_extractor.get_feature_names_out())
