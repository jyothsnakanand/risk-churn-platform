"""Unit tests for models."""

import numpy as np
import pytest
from numpy.typing import NDArray

from src.risk_churn_platform.models.risk_scorer import RiskScorerV1, RiskScorerV2


@pytest.fixture
def sample_data() -> tuple[NDArray[np.float64], NDArray[np.int_]]:
    """Generate sample training data.

    Returns:
        Tuple of features and labels
    """
    np.random.seed(42)
    X = np.random.randn(100, 8)
    y = np.random.randint(0, 2, 100)
    return X, y


def test_risk_scorer_v1_train_predict(
    sample_data: tuple[NDArray[np.float64], NDArray[np.int_]]
) -> None:
    """Test RiskScorerV1 training and prediction."""
    X, y = sample_data

    model = RiskScorerV1()
    model.train(X, y, n_estimators=10, max_depth=3)

    # Test predict
    predictions = model.predict(X[:10])
    assert predictions.shape == (10,)
    assert all(p in [0, 1] for p in predictions)

    # Test predict_proba
    probabilities = model.predict_proba(X[:10])
    assert probabilities.shape == (10, 2)
    assert all(0 <= p <= 1 for row in probabilities for p in row)
    assert all(abs(sum(row) - 1.0) < 1e-6 for row in probabilities)


def test_risk_scorer_v2_train_predict(
    sample_data: tuple[NDArray[np.float64], NDArray[np.int_]]
) -> None:
    """Test RiskScorerV2 training and prediction."""
    X, y = sample_data

    model = RiskScorerV2()
    model.train(X, y, n_estimators=10, learning_rate=0.1, max_depth=3)

    # Test predict
    predictions = model.predict(X[:10])
    assert predictions.shape == (10,)
    assert all(p in [0, 1] for p in predictions)

    # Test predict_proba
    probabilities = model.predict_proba(X[:10])
    assert probabilities.shape == (10, 2)
    assert all(0 <= p <= 1 for row in probabilities for p in row)


def test_model_metadata() -> None:
    """Test model metadata."""
    model_v1 = RiskScorerV1()
    metadata = model_v1.get_metadata()

    assert metadata["model_name"] == "risk-scorer"
    assert metadata["version"] == "v1"
    assert "type" in metadata


def test_model_not_loaded_error() -> None:
    """Test error when model not loaded."""
    model = RiskScorerV1()
    X = np.random.randn(10, 8)

    with pytest.raises(ValueError, match="Model not loaded"):
        model.predict(X)

    with pytest.raises(ValueError, match="Model not loaded"):
        model.predict_proba(X)
