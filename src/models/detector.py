"""SentinelX-Shift Models: Supervised XGBoost and Benign-Trained Anomaly Detectors.

1. Feature pipeline: log1p transform followed by StandardScaler fit on train only.
2. Supervised: XGBoost binary classifier (attack vs benign), class-weighted, early stopping on val.
3. Unsupervised: Isolation Forest and Autoencoder (MLPRegressor) trained strictly on BENIGN flows.
4. Calibration: IsotonicRegression for XGBoost, Empirical CDF for anomaly scores, guaranteeing [0, 1].
"""

from typing import Dict, List, Optional, Tuple, Union, Any
import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.isotonic import IsotonicRegression
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from xgboost import XGBClassifier
import joblib

logger = logging.getLogger(__name__)


class FeaturePipeline:
    """Log1p transform followed by StandardScaler, fit strictly on training data."""

    def __init__(self, feature_cols: List[str]):
        self.feature_cols = feature_cols
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, X: pd.DataFrame) -> "FeaturePipeline":
        X_mat = np.maximum(0, X[self.feature_cols].to_numpy(dtype=np.float64))
        X_log = np.log1p(X_mat)
        self.scaler.fit(X_log)
        self.is_fitted = True
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("FeaturePipeline must be fit before transform!")
        X_mat = np.maximum(0, X[self.feature_cols].to_numpy(dtype=np.float64))
        X_log = np.log1p(X_mat)
        return self.scaler.transform(X_log)

    def fit_transform(self, X: pd.DataFrame) -> np.ndarray:
        return self.fit(X).transform(X)


class ECDFCalibrator:
    """Maps raw continuous anomaly scores to [0, 1] using Empirical Cumulative Distribution Function."""

    def __init__(self):
        self.sorted_scores: Optional[np.ndarray] = None

    def fit(self, scores: np.ndarray) -> "ECDFCalibrator":
        clean_scores = np.sort(np.asarray(scores, dtype=np.float64).flatten())
        self.sorted_scores = clean_scores
        return self

    def predict(self, scores: np.ndarray) -> np.ndarray:
        if self.sorted_scores is None or len(self.sorted_scores) == 0:
            raise RuntimeError("ECDFCalibrator must be fit before predicting!")
        arr = np.asarray(scores, dtype=np.float64).flatten()
        # Find percentile in reference distribution
        ranks = np.searchsorted(self.sorted_scores, arr, side="right")
        calibrated = ranks / float(len(self.sorted_scores))
        return np.clip(calibrated, 0.0, 1.0)


class XGBoostDetector:
    """Supervised XGBoost binary detector with class-weighting, early stopping, and isotonic calibration."""

    def __init__(self, random_seed: int = 42, n_estimators: int = 100, max_depth: int = 4, lr: float = 0.1):
        self.random_seed = random_seed
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.lr = lr
        self.model: Optional[XGBClassifier] = None
        self.calibrator = IsotonicRegression(out_of_bounds="clip")

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> "XGBoostDetector":
        n_neg = int(np.sum(y_train == 0))
        n_pos = int(np.sum(y_train == 1))
        scale_pos_weight = float(n_neg) / float(max(1, n_pos))

        self.model = XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.lr,
            scale_pos_weight=scale_pos_weight,
            random_state=self.random_seed,
            n_jobs=2,
            eval_metric="logloss",
            early_stopping_rounds=10
        )
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        # Calibrate on validation set probabilities
        val_raw_probs = self.model.predict_proba(X_val)[:, 1]
        self.calibrator.fit(val_raw_probs, y_val)
        return self

    def predict_scores(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("XGBoostDetector must be fit first!")
        raw_probs = self.model.predict_proba(X)[:, 1]
        calibrated = self.calibrator.predict(raw_probs)
        return np.clip(calibrated, 0.0, 1.0)


class IsolationForestDetector:
    """Unsupervised anomaly detector trained exclusively on benign network flows."""

    def __init__(self, random_seed: int = 42, n_estimators: int = 100, contamination: str = "auto"):
        self.random_seed = random_seed
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_seed,
            n_jobs=2
        )
        self.calibrator = ECDFCalibrator()

    def fit(
        self,
        X_train_benign: np.ndarray,
        X_val_benign: np.ndarray,
        y_train_benign: Optional[np.ndarray] = None,
        y_val_benign: Optional[np.ndarray] = None
    ) -> "IsolationForestDetector":
        # Strict defensive check: verify no attack labels are ever passed
        if y_train_benign is not None and np.any(y_train_benign != 0):
            raise ValueError("Anomaly detector training violation: attack flows detected in X_train_benign!")
        if y_val_benign is not None and np.any(y_val_benign != 0):
            raise ValueError("Anomaly detector validation violation: attack flows detected in X_val_benign!")

        # Fit strictly on benign flows
        self.model.fit(X_train_benign)
        # Raw scores: invert score_samples so higher = more anomalous
        val_raw_scores = -self.model.score_samples(X_val_benign)
        self.calibrator.fit(val_raw_scores)
        return self

    def predict_scores(self, X: np.ndarray) -> np.ndarray:
        raw_scores = -self.model.score_samples(X)
        calibrated = self.calibrator.predict(raw_scores)
        return np.clip(calibrated, 0.0, 1.0)


class AutoencoderDetector:
    """Unsupervised Autoencoder (MLPRegressor) trained exclusively on benign flows."""

    def __init__(self, random_seed: int = 42, hidden_layers: Tuple[int, ...] = (32, 16, 32)):
        self.random_seed = random_seed
        self.model = MLPRegressor(
            hidden_layer_sizes=hidden_layers,
            activation="relu",
            max_iter=30,
            random_state=self.random_seed,
            batch_size=256,
            early_stopping=True
        )
        self.calibrator = ECDFCalibrator()

    def fit(
        self,
        X_train_benign: np.ndarray,
        X_val_benign: np.ndarray,
        y_train_benign: Optional[np.ndarray] = None,
        y_val_benign: Optional[np.ndarray] = None
    ) -> "AutoencoderDetector":
        # Strict defensive check: verify no attack labels are ever passed
        if y_train_benign is not None and np.any(y_train_benign != 0):
            raise ValueError("Anomaly detector training violation: attack flows detected in X_train_benign!")
        if y_val_benign is not None and np.any(y_val_benign != 0):
            raise ValueError("Anomaly detector validation violation: attack flows detected in X_val_benign!")

        # Fit strictly on benign flows (reconstruct X -> X)
        self.model.fit(X_train_benign, X_train_benign)
        # Reconstruction error on benign validation set
        X_val_recon = self.model.predict(X_val_benign)
        val_mse = np.mean((X_val_benign - X_val_recon) ** 2, axis=1)
        self.calibrator.fit(val_mse)
        return self

    def predict_scores(self, X: np.ndarray) -> np.ndarray:
        X_recon = self.model.predict(X)
        mse = np.mean((X - X_recon) ** 2, axis=1)
        calibrated = self.calibrator.predict(mse)
        return np.clip(calibrated, 0.0, 1.0)
