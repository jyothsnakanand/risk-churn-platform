"""Base model interface for risk/churn scoring."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

import numpy as np
from numpy.typing import NDArray


class BaseModel(ABC):
    """Abstract base class for risk/churn scoring models."""

    def __init__(self, model_name: str, version: str) -> None:
        """Initialize the base model.

        Args:
            model_name: Name of the model
            version: Version identifier
        """
        self.model_name = model_name
        self.version = version
        self.model: Any = None

    @abstractmethod
    def load(self, path: str) -> None:
        """Load model from disk.

        Args:
            path: Path to the saved model
        """
        pass

    @abstractmethod
    def predict(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        """Generate predictions.

        Args:
            features: Input features as numpy array

        Returns:
            Predictions as numpy array
        """
        pass

    @abstractmethod
    def predict_proba(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        """Generate probability predictions.

        Args:
            features: Input features as numpy array

        Returns:
            Probability predictions as numpy array
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get model metadata.

        Returns:
            Dictionary containing model metadata
        """
        return {
            "model_name": self.model_name,
            "version": self.version,
            "type": self.__class__.__name__,
        }


class SeldonModel:
    """Seldon-compatible model wrapper."""

    def __init__(self, model: BaseModel) -> None:
        """Initialize Seldon model wrapper.

        Args:
            model: Base model instance
        """
        self.model = model
        self.ready = False

    def load(self) -> bool:
        """Load the model.

        Returns:
            True if model loaded successfully
        """
        try:
            self.model.load(f"models/{self.model.version}/model.pkl")
            self.ready = True
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            self.ready = False
            return False

    def predict(
        self, X: NDArray[np.float64], features_names: List[str] | None = None
    ) -> NDArray[np.float64]:
        """Make predictions on input data.

        Args:
            X: Input features
            features_names: Optional feature names

        Returns:
            Predictions
        """
        return self.model.predict_proba(X)

    def init_metadata(self) -> Dict[str, Any]:
        """Return model metadata.

        Returns:
            Model metadata dictionary
        """
        return self.model.get_metadata()

    def health_status(self) -> Dict[str, bool]:
        """Return health status.

        Returns:
            Health status dictionary
        """
        return {"ready": self.ready}
