"""Unit tests for REST API."""

import numpy as np
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from risk_churn_platform.api.rest_api import create_app
from risk_churn_platform.models.risk_scorer import RiskScorerV1, RiskScorerV2
from risk_churn_platform.routers.model_router import ModelRouter, RoutingStrategy
from risk_churn_platform.transformers.feature_transformer import FeatureTransformer


@pytest.fixture
def mock_transformer() -> MagicMock:
    """Create mock transformer.

    Returns:
        Mock transformer
    """
    transformer = MagicMock(spec=FeatureTransformer)
    transformer.transform.return_value = np.array([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]])
    return transformer


@pytest.fixture
def mock_router() -> MagicMock:
    """Create mock router.

    Returns:
        Mock router
    """
    router = MagicMock(spec=ModelRouter)
    router.route.return_value = {
        "predictions": [np.array([0.35, 0.65])],
        "model_version": "v1",
        "strategy": "shadow",
        "latency_ms": 12.5,
        "request_id": "test-123",
    }
    router.get_metrics.return_value = {
        "strategy": "shadow",
        "v1_requests": 10,
        "v2_requests": 10,
        "total_requests": 20,
    }
    router.get_shadow_analysis.return_value = {
        "comparison_count": 5,
        "avg_prediction_diff": 0.05,
    }
    return router


@pytest.fixture
def client(mock_transformer: MagicMock, mock_router: MagicMock) -> TestClient:
    """Create test client.

    Args:
        mock_transformer: Mock transformer
        mock_router: Mock router

    Returns:
        FastAPI test client
    """
    app = create_app(
        model_router=mock_router,
        transformer=mock_transformer,
        explainer=None,
        kafka_producer=None,
    )
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "models" in data


def test_predict_endpoint(
    client: TestClient, mock_transformer: MagicMock, mock_router: MagicMock
) -> None:
    """Test prediction endpoint."""
    payload = {
        "customer_tenure": 24,
        "monthly_charges": 79.99,
        "total_charges": 1919.76,
        "contract_type": "Two year",
        "payment_method": "Credit card",
        "internet_service": "Fiber optic",
        "support_tickets": 2,
        "login_frequency": 5.2,
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert "predictions" in data
    assert data["model_version"] == "v1"
    assert data["strategy"] == "shadow"
    assert "churn_probability" in data
    assert "risk_score" in data

    # Verify transformer was called
    mock_transformer.transform.assert_called_once()

    # Verify router was called
    mock_router.route.assert_called_once()


def test_predict_invalid_data(client: TestClient) -> None:
    """Test prediction with invalid data."""
    payload = {
        "customer_tenure": -1,  # Invalid negative value
        "monthly_charges": 79.99,
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 422  # Validation error


def test_explain_endpoint_no_explainer(client: TestClient) -> None:
    """Test explain endpoint when explainer is not available."""
    payload = {
        "customer_tenure": 24,
        "monthly_charges": 79.99,
        "total_charges": 1919.76,
        "contract_type": "Two year",
        "payment_method": "Credit card",
        "internet_service": "Fiber optic",
        "support_tickets": 2,
        "login_frequency": 5.2,
    }

    response = client.post("/explain", json=payload)

    assert response.status_code == 503  # Service unavailable


def test_router_metrics_endpoint(client: TestClient, mock_router: MagicMock) -> None:
    """Test router metrics endpoint."""
    response = client.get("/router/metrics")

    assert response.status_code == 200
    data = response.json()
    assert "strategy" in data
    assert "v1_requests" in data
    assert "v2_requests" in data

    mock_router.get_metrics.assert_called_once()


def test_shadow_analysis_endpoint(client: TestClient, mock_router: MagicMock) -> None:
    """Test shadow analysis endpoint."""
    response = client.get("/router/shadow-analysis")

    assert response.status_code == 200
    data = response.json()
    assert "comparison_count" in data

    mock_router.get_shadow_analysis.assert_called_once()


def test_promote_v2_endpoint(client: TestClient, mock_router: MagicMock) -> None:
    """Test promote v2 endpoint."""
    response = client.post("/router/promote-v2")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data

    mock_router.promote_v2.assert_called_once()


def test_rollback_endpoint(client: TestClient, mock_router: MagicMock) -> None:
    """Test rollback endpoint."""
    response = client.post("/router/rollback")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data

    mock_router.rollback_to_v1.assert_called_once()


def test_predict_with_kafka(mock_transformer: MagicMock, mock_router: MagicMock) -> None:
    """Test prediction with Kafka integration."""
    mock_kafka = MagicMock()

    app = create_app(
        model_router=mock_router,
        transformer=mock_transformer,
        explainer=None,
        kafka_producer=mock_kafka,
    )
    client = TestClient(app)

    payload = {
        "customer_tenure": 24,
        "monthly_charges": 79.99,
        "total_charges": 1919.76,
        "contract_type": "Two year",
        "payment_method": "Credit card",
        "internet_service": "Fiber optic",
        "support_tickets": 2,
        "login_frequency": 5.2,
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 200

    # Verify Kafka producer was called
    mock_kafka.send_prediction.assert_called_once()


def test_explain_with_explainer(mock_transformer: MagicMock, mock_router: MagicMock) -> None:
    """Test explain endpoint with explainer available."""
    mock_explainer = MagicMock()
    mock_explainer.explain.return_value = {
        "method": "shap",
        "explanations": [{"feature_importance": {"tenure": 0.5}}],
    }

    app = create_app(
        model_router=mock_router,
        transformer=mock_transformer,
        explainer=mock_explainer,
        kafka_producer=None,
    )
    client = TestClient(app)

    payload = {
        "customer_tenure": 24,
        "monthly_charges": 79.99,
        "total_charges": 1919.76,
        "contract_type": "Two year",
        "payment_method": "Credit card",
        "internet_service": "Fiber optic",
        "support_tickets": 2,
        "login_frequency": 5.2,
    }

    response = client.post("/explain", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "shap"
    assert "explanations" in data

    mock_explainer.explain.assert_called_once()


def test_predict_error_handling(mock_transformer: MagicMock, mock_router: MagicMock) -> None:
    """Test prediction error handling."""
    # Make transformer raise an error
    mock_transformer.transform.side_effect = Exception("Transform failed")

    app = create_app(
        model_router=mock_router,
        transformer=mock_transformer,
        explainer=None,
        kafka_producer=None,
    )
    client = TestClient(app)

    payload = {
        "customer_tenure": 24,
        "monthly_charges": 79.99,
        "total_charges": 1919.76,
        "contract_type": "Two year",
        "payment_method": "Credit card",
        "internet_service": "Fiber optic",
        "support_tickets": 2,
        "login_frequency": 5.2,
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 500
    assert "Prediction failed" in response.json()["detail"]
