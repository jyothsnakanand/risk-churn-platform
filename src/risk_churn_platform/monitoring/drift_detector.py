"""Data drift detection using Alibi Detect."""

import time
from typing import Any, Dict, List

import numpy as np
import structlog
from alibi_detect.cd import KSDrift, MMDDrift, TabularDrift
from numpy.typing import NDArray

logger = structlog.get_logger()


class DriftDetector:
    """Detect data drift in production traffic."""

    def __init__(
        self,
        method: str = "ks",
        threshold: float = 0.05,
        window_size: int = 1000,
        feature_names: List[str] | None = None,
    ) -> None:
        """Initialize drift detector.

        Args:
            method: Detection method ('ks', 'mmd', 'tabular')
            threshold: P-value threshold for drift detection
            window_size: Size of sliding window for drift detection
            feature_names: Names of features
        """
        self.method = method
        self.threshold = threshold
        self.window_size = window_size
        self.feature_names = feature_names or []
        self.detector: Any = None
        self.reference_data: NDArray[np.float64] | None = None
        self.drift_history: List[Dict[str, Any]] = []
        self.current_window: List[NDArray[np.float64]] = []

    def fit(self, X_reference: NDArray[np.float64]) -> None:
        """Fit drift detector on reference data.

        Args:
            X_reference: Reference dataset (typically training data)
        """
        logger.info(
            "fitting_drift_detector",
            method=self.method,
            reference_size=len(X_reference),
        )

        self.reference_data = X_reference

        if self.method == "ks":
            self.detector = KSDrift(
                X_reference,
                p_val=self.threshold,
            )
        elif self.method == "mmd":
            self.detector = MMDDrift(
                X_reference,
                p_val=self.threshold,
                backend="pytorch",
            )
        elif self.method == "tabular":
            self.detector = TabularDrift(
                X_reference,
                p_val=self.threshold,
                categories_per_feature={},  # All numerical for now
            )
        else:
            raise ValueError(f"Unknown drift detection method: {self.method}")

    def detect(self, X: NDArray[np.float64]) -> Dict[str, Any]:
        """Detect drift in new data.

        Args:
            X: New data to check for drift

        Returns:
            Dictionary containing drift detection results
        """
        if self.detector is None:
            raise ValueError("Detector not fitted. Call fit() first.")

        # Add to current window
        self.current_window.extend(X)

        # Only check drift when window is full
        if len(self.current_window) < self.window_size:
            return {
                "is_drift": False,
                "window_filled": len(self.current_window) / self.window_size,
                "message": "Collecting samples for drift detection",
            }

        # Convert window to array
        window_data = np.array(self.current_window[: self.window_size])

        # Detect drift
        start_time = time.time()
        drift_result = self.detector.predict(window_data)
        detection_time = time.time() - start_time

        is_drift = bool(drift_result["data"]["is_drift"])
        p_value = float(drift_result["data"]["p_val"])

        # Feature-level drift (if available)
        feature_drift = {}
        if "distance" in drift_result["data"]:
            distances = drift_result["data"]["distance"]
            if len(distances) == len(self.feature_names):
                feature_drift = dict(zip(self.feature_names, distances.tolist()))

        result = {
            "is_drift": is_drift,
            "p_value": p_value,
            "threshold": self.threshold,
            "method": self.method,
            "window_size": self.window_size,
            "detection_time_ms": detection_time * 1000,
            "timestamp": time.time(),
            "feature_drift": feature_drift,
        }

        # Log drift event
        if is_drift:
            logger.warning(
                "drift_detected",
                p_value=p_value,
                threshold=self.threshold,
                method=self.method,
            )

        self.drift_history.append(result)

        # Slide window
        self.current_window = self.current_window[self.window_size // 2 :]

        return result

    def get_drift_summary(self) -> Dict[str, Any]:
        """Get summary of drift detection history.

        Returns:
            Summary statistics
        """
        if not self.drift_history:
            return {"status": "no_data"}

        drift_events = sum(1 for d in self.drift_history if d["is_drift"])
        total_checks = len(self.drift_history)

        return {
            "total_checks": total_checks,
            "drift_events": drift_events,
            "drift_rate": drift_events / total_checks if total_checks > 0 else 0,
            "avg_p_value": np.mean([d["p_value"] for d in self.drift_history]),
            "last_check": self.drift_history[-1] if self.drift_history else None,
        }

    def reset_window(self) -> None:
        """Reset the current window."""
        self.current_window = []
        logger.info("drift_detector_window_reset")
