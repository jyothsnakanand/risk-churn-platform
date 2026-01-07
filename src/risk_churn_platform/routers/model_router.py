"""Model router for A/B testing and deployment strategies."""

import random
import time
from enum import Enum
from typing import Any, Dict, List

import numpy as np
import structlog
from numpy.typing import NDArray

from ..models.base import BaseModel

logger = structlog.get_logger()


class RoutingStrategy(Enum):
    """Available routing strategies."""

    BLUE_GREEN = "blue-green"
    CANARY = "canary"
    SHADOW = "shadow"


class ModelRouter:
    """Route requests between model versions with various strategies."""

    def __init__(
        self,
        model_v1: BaseModel,
        model_v2: BaseModel,
        strategy: RoutingStrategy = RoutingStrategy.SHADOW,
        canary_weight: float = 0.1,
        shadow_log_predictions: bool = True,
    ) -> None:
        """Initialize the model router.

        Args:
            model_v1: Version 1 of the model
            model_v2: Version 2 of the model
            strategy: Routing strategy to use
            canary_weight: Percentage of traffic for v2 in canary mode (0.0-1.0)
            shadow_log_predictions: Whether to log shadow predictions
        """
        self.model_v1 = model_v1
        self.model_v2 = model_v2
        self.strategy = strategy
        self.canary_weight = canary_weight
        self.shadow_log_predictions = shadow_log_predictions

        # Metrics
        self.v1_requests = 0
        self.v2_requests = 0
        self.shadow_comparisons: List[Dict[str, Any]] = []

    def route(
        self, features: NDArray[np.float64], request_id: str | None = None
    ) -> Dict[str, Any]:
        """Route prediction request based on configured strategy.

        Args:
            features: Input features
            request_id: Optional request identifier

        Returns:
            Prediction result with metadata
        """
        if self.strategy == RoutingStrategy.BLUE_GREEN:
            return self._blue_green_route(features, request_id)
        elif self.strategy == RoutingStrategy.CANARY:
            return self._canary_route(features, request_id)
        elif self.strategy == RoutingStrategy.SHADOW:
            return self._shadow_route(features, request_id)
        else:
            raise ValueError(f"Unknown routing strategy: {self.strategy}")

    def _blue_green_route(
        self, features: NDArray[np.float64], request_id: str | None = None
    ) -> Dict[str, Any]:
        """Blue-green deployment: all traffic to one version.

        Args:
            features: Input features
            request_id: Optional request identifier

        Returns:
            Prediction result
        """
        # In production, you'd have a config flag to switch between versions
        # For now, always use v2 in blue-green mode
        start_time = time.time()
        predictions = self.model_v2.predict_proba(features)
        latency = time.time() - start_time

        self.v2_requests += 1

        return {
            "predictions": predictions.tolist(),
            "model_version": self.model_v2.version,
            "strategy": "blue-green",
            "latency_ms": latency * 1000,
            "request_id": request_id,
        }

    def _canary_route(
        self, features: NDArray[np.float64], request_id: str | None = None
    ) -> Dict[str, Any]:
        """Canary deployment: percentage-based traffic splitting.

        Args:
            features: Input features
            request_id: Optional request identifier

        Returns:
            Prediction result
        """
        # Randomly route based on canary weight
        use_v2 = random.random() < self.canary_weight

        start_time = time.time()
        if use_v2:
            predictions = self.model_v2.predict_proba(features)
            model_version = self.model_v2.version
            self.v2_requests += 1
        else:
            predictions = self.model_v1.predict_proba(features)
            model_version = self.model_v1.version
            self.v1_requests += 1

        latency = time.time() - start_time

        logger.info(
            "canary_routing",
            model_version=model_version,
            canary_weight=self.canary_weight,
            request_id=request_id,
        )

        return {
            "predictions": predictions.tolist(),
            "model_version": model_version,
            "strategy": "canary",
            "canary_weight": self.canary_weight,
            "latency_ms": latency * 1000,
            "request_id": request_id,
        }

    def _shadow_route(
        self, features: NDArray[np.float64], request_id: str | None = None
    ) -> Dict[str, Any]:
        """Shadow deployment: v1 serves traffic, v2 runs in parallel.

        Args:
            features: Input features
            request_id: Optional request identifier

        Returns:
            Prediction result from v1, with v2 comparison logged
        """
        # Primary prediction from v1
        start_time_v1 = time.time()
        predictions_v1 = self.model_v1.predict_proba(features)
        latency_v1 = time.time() - start_time_v1
        self.v1_requests += 1

        # Shadow prediction from v2 (async in production)
        start_time_v2 = time.time()
        predictions_v2 = self.model_v2.predict_proba(features)
        latency_v2 = time.time() - start_time_v2
        self.v2_requests += 1

        # Compare predictions
        prediction_diff = np.abs(predictions_v1 - predictions_v2).mean()

        comparison = {
            "request_id": request_id,
            "v1_predictions": predictions_v1.tolist(),
            "v2_predictions": predictions_v2.tolist(),
            "prediction_diff": float(prediction_diff),
            "v1_latency_ms": latency_v1 * 1000,
            "v2_latency_ms": latency_v2 * 1000,
            "timestamp": time.time(),
        }

        self.shadow_comparisons.append(comparison)

        if self.shadow_log_predictions:
            logger.info(
                "shadow_comparison",
                prediction_diff=prediction_diff,
                latency_diff_ms=(latency_v2 - latency_v1) * 1000,
                request_id=request_id,
            )

        # Return v1 predictions to client
        return {
            "predictions": predictions_v1.tolist(),
            "model_version": self.model_v1.version,
            "strategy": "shadow",
            "shadow_comparison": comparison,
            "latency_ms": latency_v1 * 1000,
            "request_id": request_id,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get routing metrics.

        Returns:
            Dictionary containing routing metrics
        """
        total_requests = self.v1_requests + self.v2_requests
        return {
            "strategy": self.strategy.value,
            "v1_requests": self.v1_requests,
            "v2_requests": self.v2_requests,
            "total_requests": total_requests,
            "v1_percentage": (
                self.v1_requests / total_requests if total_requests > 0 else 0
            ),
            "v2_percentage": (
                self.v2_requests / total_requests if total_requests > 0 else 0
            ),
            "shadow_comparisons_count": len(self.shadow_comparisons),
        }

    def get_shadow_analysis(self) -> Dict[str, Any]:
        """Analyze shadow deployment results.

        Returns:
            Analysis of shadow predictions
        """
        if not self.shadow_comparisons:
            return {"status": "no_data"}

        diffs = [comp["prediction_diff"] for comp in self.shadow_comparisons]
        v1_latencies = [comp["v1_latency_ms"] for comp in self.shadow_comparisons]
        v2_latencies = [comp["v2_latency_ms"] for comp in self.shadow_comparisons]

        return {
            "comparison_count": len(self.shadow_comparisons),
            "avg_prediction_diff": np.mean(diffs),
            "max_prediction_diff": np.max(diffs),
            "avg_v1_latency_ms": np.mean(v1_latencies),
            "avg_v2_latency_ms": np.mean(v2_latencies),
            "latency_improvement_pct": (
                ((np.mean(v1_latencies) - np.mean(v2_latencies)) / np.mean(v1_latencies))
                * 100
            ),
        }

    def promote_v2(self) -> None:
        """Promote v2 to primary (switch to blue-green with v2)."""
        logger.info("promoting_v2_to_primary")
        self.strategy = RoutingStrategy.BLUE_GREEN

    def rollback_to_v1(self) -> None:
        """Rollback to v1."""
        logger.info("rolling_back_to_v1")
        self.strategy = RoutingStrategy.BLUE_GREEN
        # Swap the models
        self.model_v1, self.model_v2 = self.model_v2, self.model_v1
