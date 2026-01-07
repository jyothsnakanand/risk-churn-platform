"""Unit tests for monitoring components."""

import numpy as np
import pytest
from numpy.typing import NDArray

from risk_churn_platform.monitoring.alerting import (
    Alert,
    AlertManager,
    AlertSeverity,
    LogAlertHandler,
)
from risk_churn_platform.monitoring.drift_detector import DriftDetector
from risk_churn_platform.monitoring.outlier_detector import OutlierDetector


@pytest.fixture
def reference_data() -> NDArray[np.float64]:
    """Generate reference data for detectors.

    Returns:
        Reference dataset
    """
    np.random.seed(42)
    return np.random.randn(1000, 8)


@pytest.fixture
def test_data() -> NDArray[np.float64]:
    """Generate test data (no drift).

    Returns:
        Test dataset from same distribution
    """
    np.random.seed(43)
    return np.random.randn(100, 8)


@pytest.fixture
def drifted_data() -> NDArray[np.float64]:
    """Generate drifted data.

    Returns:
        Test dataset from different distribution
    """
    np.random.seed(44)
    return np.random.randn(100, 8) + 2.0  # Shifted distribution


# Drift Detector Tests


def test_drift_detector_initialization() -> None:
    """Test drift detector initialization."""
    detector = DriftDetector(method="ks", threshold=0.05, window_size=100)

    assert detector.method == "ks"
    assert detector.threshold == 0.05
    assert detector.window_size == 100
    assert detector.detector is None
    assert len(detector.drift_history) == 0


def test_drift_detector_fit(reference_data: NDArray[np.float64]) -> None:
    """Test fitting drift detector."""
    detector = DriftDetector(method="ks", threshold=0.05)
    detector.fit(reference_data)

    assert detector.detector is not None
    assert detector.reference_data is not None


def test_drift_detector_no_drift(
    reference_data: NDArray[np.float64], test_data: NDArray[np.float64]
) -> None:
    """Test drift detection with no drift."""
    detector = DriftDetector(method="ks", threshold=0.05, window_size=100)
    detector.fit(reference_data)

    result = detector.detect(test_data)

    assert "is_drift" in result
    assert "window_filled" in result or "p_value" in result


def test_drift_detector_window_filling(
    reference_data: NDArray[np.float64], test_data: NDArray[np.float64]
) -> None:
    """Test drift detector window filling."""
    detector = DriftDetector(method="ks", threshold=0.05, window_size=1000)
    detector.fit(reference_data)

    # Send small batch
    small_batch = test_data[:10]
    result = detector.detect(small_batch)

    # Should indicate window is still filling
    assert "window_filled" in result


def test_drift_detector_summary(reference_data: NDArray[np.float64]) -> None:
    """Test drift summary with no data."""
    detector = DriftDetector(method="ks")
    detector.fit(reference_data)

    summary = detector.get_drift_summary()

    assert summary["status"] == "no_data"


def test_drift_detector_reset_window(reference_data: NDArray[np.float64]) -> None:
    """Test resetting drift detector window."""
    detector = DriftDetector(method="ks", window_size=100)
    detector.fit(reference_data)

    # Add some data
    detector.current_window = [np.array([1, 2, 3])]

    # Reset
    detector.reset_window()

    assert len(detector.current_window) == 0


# Outlier Detector Tests


def test_outlier_detector_initialization() -> None:
    """Test outlier detector initialization."""
    detector = OutlierDetector(method="isolation_forest", threshold=0.1, contamination=0.1)

    assert detector.method == "isolation_forest"
    assert detector.threshold == 0.1
    assert detector.contamination == 0.1
    assert detector.detector is None


def test_outlier_detector_fit(reference_data: NDArray[np.float64]) -> None:
    """Test fitting outlier detector."""
    detector = OutlierDetector(method="isolation_forest")
    detector.fit(reference_data)

    assert detector.detector is not None


def test_outlier_detector_detect(
    reference_data: NDArray[np.float64], test_data: NDArray[np.float64]
) -> None:
    """Test outlier detection."""
    detector = OutlierDetector(method="isolation_forest", contamination=0.1)
    detector.fit(reference_data)

    result = detector.detect(test_data)

    assert "num_samples" in result
    assert "num_outliers" in result
    assert "outlier_rate" in result
    assert "is_outlier" in result
    assert "outlier_scores" in result
    assert result["num_samples"] == len(test_data)


def test_outlier_detector_summary(reference_data: NDArray[np.float64]) -> None:
    """Test outlier summary with no data."""
    detector = OutlierDetector(method="isolation_forest")
    detector.fit(reference_data)

    summary = detector.get_outlier_summary()

    assert summary["status"] == "no_data"


def test_outlier_detector_with_data(
    reference_data: NDArray[np.float64], test_data: NDArray[np.float64]
) -> None:
    """Test outlier detection and summary."""
    detector = OutlierDetector(method="isolation_forest")
    detector.fit(reference_data)

    # Detect outliers
    detector.detect(test_data)

    # Get summary
    summary = detector.get_outlier_summary()

    assert "total_samples" in summary
    assert "total_outliers" in summary
    assert "overall_outlier_rate" in summary
    assert summary["total_samples"] == len(test_data)


# Alerting Tests


def test_alert_creation() -> None:
    """Test creating an alert."""
    from datetime import datetime

    alert = Alert(
        alert_type="drift_detected",
        severity=AlertSeverity.WARNING,
        message="Drift detected in feature X",
        details={"p_value": 0.01},
        timestamp=datetime.now(),
        source="test",
    )

    assert alert.alert_type == "drift_detected"
    assert alert.severity == AlertSeverity.WARNING
    assert alert.message == "Drift detected in feature X"


def test_alert_to_dict() -> None:
    """Test converting alert to dictionary."""
    from datetime import datetime

    alert = Alert(
        alert_type="test",
        severity=AlertSeverity.INFO,
        message="Test message",
        details={},
        timestamp=datetime.now(),
        source="test",
    )

    alert_dict = alert.to_dict()

    assert alert_dict["alert_type"] == "test"
    assert alert_dict["severity"] == "info"
    assert "timestamp" in alert_dict


def test_log_alert_handler() -> None:
    """Test log alert handler."""
    from datetime import datetime

    handler = LogAlertHandler()
    alert = Alert(
        alert_type="test",
        severity=AlertSeverity.INFO,
        message="Test alert",
        details={},
        timestamp=datetime.now(),
        source="test",
    )

    # Should not raise
    handler.send_alert(alert)


def test_alert_manager_add_handler() -> None:
    """Test adding alert handler."""
    manager = AlertManager()
    handler = LogAlertHandler()

    initial_count = len(manager.handlers)
    manager.add_handler(handler)

    assert len(manager.handlers) == initial_count + 1


def test_alert_manager_send_alert() -> None:
    """Test sending alert through manager."""
    manager = AlertManager()
    manager.add_handler(LogAlertHandler())

    manager.send_alert(
        alert_type="test",
        severity=AlertSeverity.INFO,
        message="Test message",
        details={"key": "value"},
    )

    assert len(manager.alert_history) == 1
    assert manager.alert_history[0].alert_type == "test"


def test_alert_manager_get_recent_alerts() -> None:
    """Test getting recent alerts."""
    manager = AlertManager()

    # Send several alerts
    for i in range(5):
        manager.send_alert(
            alert_type=f"test_{i}", severity=AlertSeverity.INFO, message=f"Test message {i}"
        )

    recent = manager.get_recent_alerts(limit=3)

    assert len(recent) == 3


def test_alert_manager_filter_by_severity() -> None:
    """Test filtering alerts by severity."""
    manager = AlertManager()

    # Send different severity alerts
    manager.send_alert(
        alert_type="warning_alert", severity=AlertSeverity.WARNING, message="Warning"
    )
    manager.send_alert(alert_type="info_alert", severity=AlertSeverity.INFO, message="Info")

    warnings = manager.get_recent_alerts(severity=AlertSeverity.WARNING)

    assert len(warnings) == 1
    assert warnings[0]["alert_type"] == "warning_alert"
