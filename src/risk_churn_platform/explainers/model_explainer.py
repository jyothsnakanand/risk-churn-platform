"""Model explainability using SHAP and Alibi."""

from typing import Any, Dict, List

import numpy as np
import shap
import structlog
from alibi.explainers import AnchorTabular
from numpy.typing import NDArray

from ..models.base import BaseModel

logger = structlog.get_logger()


class ModelExplainer:
    """Generate explanations for model predictions."""

    def __init__(
        self,
        model: BaseModel,
        method: str = "shap",
        feature_names: List[str] | None = None,
    ) -> None:
        """Initialize the explainer.

        Args:
            model: Model to explain
            method: Explanation method ('shap' or 'anchor')
            feature_names: Names of input features
        """
        self.model = model
        self.method = method
        self.feature_names = feature_names or []
        self.explainer: Any = None

    def fit(
        self,
        X_background: NDArray[np.float64],
        categorical_features: List[int] | None = None,
    ) -> None:
        """Initialize the explainer with background data.

        Args:
            X_background: Background dataset for SHAP
            categorical_features: Indices of categorical features for Anchor
        """
        if self.method == "shap":
            self._init_shap_explainer(X_background)
        elif self.method == "anchor":
            self._init_anchor_explainer(X_background, categorical_features or [])
        else:
            raise ValueError(f"Unknown explanation method: {self.method}")

    def _init_shap_explainer(self, X_background: NDArray[np.float64]) -> None:
        """Initialize SHAP explainer.

        Args:
            X_background: Background dataset
        """
        logger.info("initializing_shap_explainer", background_size=len(X_background))

        # Use TreeExplainer if model supports it, otherwise use KernelExplainer
        try:
            self.explainer = shap.TreeExplainer(self.model.model)
        except Exception:
            # Fallback to KernelExplainer for non-tree models
            self.explainer = shap.KernelExplainer(
                self.model.predict_proba, X_background
            )

    def _init_anchor_explainer(
        self, X_background: NDArray[np.float64], categorical_features: List[int]
    ) -> None:
        """Initialize Anchor explainer.

        Args:
            X_background: Background dataset
            categorical_features: Indices of categorical features
        """
        logger.info(
            "initializing_anchor_explainer",
            background_size=len(X_background),
            categorical_features=categorical_features,
        )

        self.explainer = AnchorTabular(
            predictor=self.model.predict,
            feature_names=self.feature_names,
        )
        self.explainer.fit(X_background, categorical_features=categorical_features)

    def explain(
        self, X: NDArray[np.float64], threshold: float = 0.95
    ) -> Dict[str, Any]:
        """Generate explanation for predictions.

        Args:
            X: Input features to explain
            threshold: Confidence threshold for Anchor explanations

        Returns:
            Dictionary containing explanations
        """
        if self.explainer is None:
            raise ValueError("Explainer not initialized. Call fit() first.")

        if self.method == "shap":
            return self._explain_shap(X)
        elif self.method == "anchor":
            return self._explain_anchor(X, threshold)
        else:
            raise ValueError(f"Unknown explanation method: {self.method}")

    def _explain_shap(self, X: NDArray[np.float64]) -> Dict[str, Any]:
        """Generate SHAP explanations.

        Args:
            X: Input features

        Returns:
            SHAP values and explanation details
        """
        shap_values = self.explainer.shap_values(X)

        # Handle multi-class case
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # Use positive class for binary classification

        explanations = []
        for i in range(len(X)):
            feature_importance = {}
            for j, feature_name in enumerate(self.feature_names):
                feature_importance[feature_name] = float(shap_values[i, j])

            # Sort by absolute importance
            sorted_features = sorted(
                feature_importance.items(),
                key=lambda x: abs(x[1]),
                reverse=True,
            )

            explanations.append(
                {
                    "feature_importance": dict(sorted_features[:5]),  # Top 5 features
                    "all_shap_values": feature_importance,
                }
            )

        return {
            "method": "shap",
            "explanations": explanations,
        }

    def _explain_anchor(
        self, X: NDArray[np.float64], threshold: float
    ) -> Dict[str, Any]:
        """Generate Anchor explanations.

        Args:
            X: Input features
            threshold: Confidence threshold

        Returns:
            Anchor rules and explanation details
        """
        explanations = []
        for i in range(len(X)):
            explanation = self.explainer.explain(X[i], threshold=threshold)

            explanations.append(
                {
                    "anchor_rule": explanation.anchor,
                    "precision": float(explanation.precision),
                    "coverage": float(explanation.coverage),
                }
            )

        return {
            "method": "anchor",
            "explanations": explanations,
        }


class SeldonExplainer:
    """Seldon-compatible explainer wrapper."""

    def __init__(self, explainer: ModelExplainer) -> None:
        """Initialize Seldon explainer wrapper.

        Args:
            explainer: Model explainer instance
        """
        self.explainer = explainer
        self.ready = False

    def load(self) -> bool:
        """Load the explainer.

        Returns:
            True if explainer loaded successfully
        """
        self.ready = True
        return True

    def explain(
        self, X: NDArray[np.float64], feature_names: List[str] | None = None
    ) -> Dict[str, Any]:
        """Generate explanations.

        Args:
            X: Input features
            feature_names: Feature names

        Returns:
            Explanations
        """
        return self.explainer.explain(X)

    def health_status(self) -> Dict[str, bool]:
        """Return health status.

        Returns:
            Health status dictionary
        """
        return {"ready": self.ready}
