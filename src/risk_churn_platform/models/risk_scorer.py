"""Risk/Churn scoring model implementations."""

import joblib
import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier

from .base import BaseModel


class RiskScorerV1(BaseModel):
    """Version 1 of the risk/churn scoring model using Random Forest."""

    def __init__(self) -> None:
        """Initialize Risk Scorer V1."""
        super().__init__(model_name="risk-scorer", version="v1")
        self.model: RandomForestClassifier | None = None

    def load(self, path: str) -> None:
        """Load the trained model from disk.

        Args:
            path: Path to the saved model file
        """
        self.model = joblib.load(path)

    def predict(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        """Generate class predictions.

        Args:
            features: Input features

        Returns:
            Predicted classes (0 or 1)
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load() first.")
        return self.model.predict(features)

    def predict_proba(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        """Generate probability predictions.

        Args:
            features: Input features

        Returns:
            Probability predictions for each class
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load() first.")
        return self.model.predict_proba(features)

    def train(
        self,
        X_train: NDArray[np.float64],
        y_train: NDArray[np.int_],
        n_estimators: int = 100,
        max_depth: int = 10,
    ) -> None:
        """Train the model.

        Args:
            X_train: Training features
            y_train: Training labels
            n_estimators: Number of trees
            max_depth: Maximum depth of trees
        """
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_train, y_train)

    def save(self, path: str) -> None:
        """Save the model to disk.

        Args:
            path: Path where model should be saved
        """
        if self.model is None:
            raise ValueError("No model to save. Train a model first.")
        joblib.dump(self.model, path)


class RiskScorerV2(BaseModel):
    """Version 2 of the risk/churn scoring model using Gradient Boosting."""

    def __init__(self) -> None:
        """Initialize Risk Scorer V2."""
        super().__init__(model_name="risk-scorer", version="v2")
        self.model: GradientBoostingClassifier | None = None

    def load(self, path: str) -> None:
        """Load the trained model from disk.

        Args:
            path: Path to the saved model file
        """
        self.model = joblib.load(path)

    def predict(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        """Generate class predictions.

        Args:
            features: Input features

        Returns:
            Predicted classes (0 or 1)
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load() first.")
        return self.model.predict(features)

    def predict_proba(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        """Generate probability predictions.

        Args:
            features: Input features

        Returns:
            Probability predictions for each class
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load() first.")
        return self.model.predict_proba(features)

    def train(
        self,
        X_train: NDArray[np.float64],
        y_train: NDArray[np.int_],
        n_estimators: int = 200,
        learning_rate: float = 0.1,
        max_depth: int = 5,
    ) -> None:
        """Train the model.

        Args:
            X_train: Training features
            y_train: Training labels
            n_estimators: Number of boosting stages
            learning_rate: Learning rate
            max_depth: Maximum depth of trees
        """
        self.model = GradientBoostingClassifier(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            random_state=42,
        )
        self.model.fit(X_train, y_train)

    def save(self, path: str) -> None:
        """Save the model to disk.

        Args:
            path: Path where model should be saved
        """
        if self.model is None:
            raise ValueError("No model to save. Train a model first.")
        joblib.dump(self.model, path)
