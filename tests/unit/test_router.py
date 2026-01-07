"""Unit tests for model router."""

import numpy as np
import pytest

from src.risk_churn_platform.models.risk_scorer import RiskScorerV1, RiskScorerV2
from src.risk_churn_platform.routers.model_router import ModelRouter, RoutingStrategy


@pytest.fixture
def trained_models() -> tuple[RiskScorerV1, RiskScorerV2]:
    """Create trained model instances.

    Returns:
        Tuple of trained v1 and v2 models
    """
    np.random.seed(42)
    X = np.random.randn(100, 8)
    y = np.random.randint(0, 2, 100)

    model_v1 = RiskScorerV1()
    model_v1.train(X, y, n_estimators=10, max_depth=3)

    model_v2 = RiskScorerV2()
    model_v2.train(X, y, n_estimators=10, learning_rate=0.1, max_depth=3)

    return model_v1, model_v2


def test_shadow_routing(trained_models: tuple[RiskScorerV1, RiskScorerV2]) -> None:
    """Test shadow routing strategy."""
    model_v1, model_v2 = trained_models

    router = ModelRouter(
        model_v1=model_v1,
        model_v2=model_v2,
        strategy=RoutingStrategy.SHADOW,
    )

    features = np.random.randn(5, 8)
    result = router.route(features, request_id="test-123")

    # Shadow mode returns v1 predictions
    assert result["model_version"] == "v1"
    assert result["strategy"] == "shadow"
    assert "predictions" in result
    assert "shadow_comparison" in result
    assert result["request_id"] == "test-123"

    # Check shadow comparison
    comparison = result["shadow_comparison"]
    assert "v1_predictions" in comparison
    assert "v2_predictions" in comparison
    assert "prediction_diff" in comparison


def test_canary_routing(trained_models: tuple[RiskScorerV1, RiskScorerV2]) -> None:
    """Test canary routing strategy."""
    model_v1, model_v2 = trained_models

    router = ModelRouter(
        model_v1=model_v1,
        model_v2=model_v2,
        strategy=RoutingStrategy.CANARY,
        canary_weight=0.5,  # 50/50 split for testing
    )

    features = np.random.randn(5, 8)

    # Run multiple requests to test distribution
    v1_count = 0
    v2_count = 0
    for _ in range(100):
        result = router.route(features)
        if result["model_version"] == "v1":
            v1_count += 1
        else:
            v2_count += 1

    # Should be roughly 50/50 with some variance
    assert 30 <= v1_count <= 70
    assert 30 <= v2_count <= 70


def test_blue_green_routing(trained_models: tuple[RiskScorerV1, RiskScorerV2]) -> None:
    """Test blue-green routing strategy."""
    model_v1, model_v2 = trained_models

    router = ModelRouter(
        model_v1=model_v1,
        model_v2=model_v2,
        strategy=RoutingStrategy.BLUE_GREEN,
    )

    features = np.random.randn(5, 8)
    result = router.route(features)

    # Blue-green uses v2 by default
    assert result["model_version"] == "v2"
    assert result["strategy"] == "blue-green"


def test_router_metrics(trained_models: tuple[RiskScorerV1, RiskScorerV2]) -> None:
    """Test router metrics collection."""
    model_v1, model_v2 = trained_models

    router = ModelRouter(
        model_v1=model_v1,
        model_v2=model_v2,
        strategy=RoutingStrategy.SHADOW,
    )

    features = np.random.randn(5, 8)

    # Make some requests
    for _ in range(10):
        router.route(features)

    metrics = router.get_metrics()

    assert metrics["strategy"] == "shadow"
    assert metrics["total_requests"] == 20  # Both v1 and v2 in shadow mode
    assert metrics["v1_requests"] == 10
    assert metrics["v2_requests"] == 10


def test_shadow_analysis(trained_models: tuple[RiskScorerV1, RiskScorerV2]) -> None:
    """Test shadow deployment analysis."""
    model_v1, model_v2 = trained_models

    router = ModelRouter(
        model_v1=model_v1,
        model_v2=model_v2,
        strategy=RoutingStrategy.SHADOW,
    )

    features = np.random.randn(5, 8)

    # Make requests
    for _ in range(5):
        router.route(features)

    analysis = router.get_shadow_analysis()

    assert "comparison_count" in analysis
    assert "avg_prediction_diff" in analysis
    assert "avg_v1_latency_ms" in analysis
    assert "avg_v2_latency_ms" in analysis
    assert analysis["comparison_count"] == 5


def test_promote_v2(trained_models: tuple[RiskScorerV1, RiskScorerV2]) -> None:
    """Test v2 promotion."""
    model_v1, model_v2 = trained_models

    router = ModelRouter(
        model_v1=model_v1,
        model_v2=model_v2,
        strategy=RoutingStrategy.SHADOW,
    )

    router.promote_v2()

    assert router.strategy == RoutingStrategy.BLUE_GREEN
