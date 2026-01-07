"""Outlier detection using Alibi Detect."""

import time
from typing import Any

import numpy as np
import structlog
from alibi_detect.od import IForest, Mahalanobis
from numpy.typing import NDArray

logger = structlog.get_logger()


class OutlierDetector:
    """Detect outliers in production traffic."""

    def __init__(
        self,
        method: str = "isolation_forest",
        threshold: float = 0.1,
        contamination: float = 0.1,
    ) -> None:
        """Initialize outlier detector.

        Args:
            method: Detection method ('isolation_forest', 'mahalanobis')
            threshold: Outlier score threshold
            contamination: Expected proportion of outliers
        """
        self.method = method
        self.threshold = threshold
        self.contamination = contamination
        self.detector: Any = None
        self.outlier_history: list[dict[str, Any]] = []

    def fit(self, X_train: NDArray[np.float64]) -> None:
        """Fit outlier detector on training data.

        Args:
            X_train: Training dataset
        """
        logger.info(
            "fitting_outlier_detector",
            method=self.method,
            training_size=len(X_train),
        )

        if self.method == "isolation_forest":
            self.detector = IForest(threshold=self.threshold)
            self.detector.fit(X_train)
        elif self.method == "mahalanobis":
            self.detector = Mahalanobis(threshold=self.threshold)
            self.detector.fit(X_train)
        else:
            raise ValueError(f"Unknown outlier detection method: {self.method}")

    def detect(self, X: NDArray[np.float64]) -> dict[str, Any]:
        """Detect outliers in new data.

        Args:
            X: New data to check for outliers

        Returns:
            Dictionary containing outlier detection results
        """
        if self.detector is None:
            raise ValueError("Detector not fitted. Call fit() first.")

        start_time = time.time()
        outlier_result = self.detector.predict(X)
        detection_time = time.time() - start_time

        # Extract results
        is_outlier = outlier_result["data"]["is_outlier"]
        outlier_scores = outlier_result["data"]["instance_score"]

        # Count outliers
        num_outliers = int(np.sum(is_outlier))
        outlier_rate = num_outliers / len(X) if len(X) > 0 else 0

        result = {
            "num_samples": len(X),
            "num_outliers": num_outliers,
            "outlier_rate": outlier_rate,
            "is_outlier": is_outlier.tolist(),
            "outlier_scores": outlier_scores.tolist(),
            "threshold": self.threshold,
            "method": self.method,
            "detection_time_ms": detection_time * 1000,
            "timestamp": time.time(),
        }

        # Log significant outlier events
        if outlier_rate > self.contamination * 2:
            logger.warning(
                "high_outlier_rate",
                outlier_rate=outlier_rate,
                expected_rate=self.contamination,
                method=self.method,
            )

        self.outlier_history.append(result)

        return result

    def get_outlier_summary(self) -> dict[str, Any]:
        """Get summary of outlier detection history.

        Returns:
            Summary statistics
        """
        if not self.outlier_history:
            return {"status": "no_data"}

        total_samples = sum(h["num_samples"] for h in self.outlier_history)
        total_outliers = sum(h["num_outliers"] for h in self.outlier_history)

        return {
            "total_samples": total_samples,
            "total_outliers": total_outliers,
            "overall_outlier_rate": (total_outliers / total_samples if total_samples > 0 else 0),
            "avg_outlier_rate": np.mean([h["outlier_rate"] for h in self.outlier_history]),
            "max_outlier_rate": max(h["outlier_rate"] for h in self.outlier_history),
            "detection_count": len(self.outlier_history),
            "last_detection": self.outlier_history[-1] if self.outlier_history else None,
        }
