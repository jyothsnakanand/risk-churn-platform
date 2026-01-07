"""Unit tests for model explainer."""

import numpy as np
import pytest
from numpy.typing import NDArray
from unittest.mock import MagicMock, patch

from risk_churn_platform.explainers.model_explainer import ModelExplainer, SeldonExplainer
from risk_churn_platform.models.risk_scorer import RiskScorerV1


@pytest.fixture
def trained_model() -> RiskScorerV1:
    """Create a trained model.

    Returns:
        Trained model
    """
    np.random.seed(42)
    X = np.random.randn(100, 8)
    y = np.random.randint(0, 2, 100)

    model = RiskScorerV1()
    model.train(X, y, n_estimators=10, max_depth=3)
    return model


@pytest.fixture
def background_data() -> NDArray[np.float64]:
    """Generate background data for explainer.

    Returns:
        Background dataset
    """
    np.random.seed(42)
    return np.random.randn(50, 8)


@pytest.fixture
def test_data() -> NDArray[np.float64]:
    """Generate test data for explanation.

    Returns:
        Test dataset
    """
    np.random.seed(43)
    return np.random.randn(5, 8)


def test_explainer_initialization(trained_model: RiskScorerV1) -> None:
    """Test explainer initialization."""
    feature_names = [f"feature_{i}" for i in range(8)]
    explainer = ModelExplainer(
        model=trained_model,
        method="shap",
        feature_names=feature_names
    )

    assert explainer.model == trained_model
    assert explainer.method == "shap"
    assert explainer.feature_names == feature_names
    assert explainer.explainer is None


def test_explainer_fit_shap(
    trained_model: RiskScorerV1, background_data: NDArray[np.float64]
) -> None:
    """Test fitting SHAP explainer."""
    explainer = ModelExplainer(model=trained_model, method="shap")
    explainer.fit(background_data)

    assert explainer.explainer is not None


def test_explainer_explain_shap(
    trained_model: RiskScorerV1,
    background_data: NDArray[np.float64],
    test_data: NDArray[np.float64]
) -> None:
    """Test generating SHAP explanations."""
    feature_names = [f"feature_{i}" for i in range(8)]
    explainer = ModelExplainer(
        model=trained_model,
        method="shap",
        feature_names=feature_names
    )
    explainer.fit(background_data)

    explanations = explainer.explain(test_data)

    assert explanations["method"] == "shap"
    assert "explanations" in explanations
    assert len(explanations["explanations"]) == len(test_data)

    # Check first explanation
    first_exp = explanations["explanations"][0]
    assert "feature_importance" in first_exp
    assert "all_shap_values" in first_exp
    assert len(first_exp["feature_importance"]) <= 5  # Top 5 features


def test_explainer_not_fitted_error(
    trained_model: RiskScorerV1, test_data: NDArray[np.float64]
) -> None:
    """Test error when explainer not fitted."""
    explainer = ModelExplainer(model=trained_model, method="shap")

    with pytest.raises(ValueError, match="Explainer not initialized"):
        explainer.explain(test_data)


def test_explainer_unknown_method(trained_model: RiskScorerV1) -> None:
    """Test error with unknown explanation method."""
    explainer = ModelExplainer(model=trained_model, method="unknown")

    with pytest.raises(ValueError, match="Unknown explanation method"):
        explainer.fit(np.random.randn(50, 8))


def test_explainer_anchor_initialization(
    trained_model: RiskScorerV1, background_data: NDArray[np.float64]
) -> None:
    """Test Anchor explainer initialization."""
    feature_names = [f"feature_{i}" for i in range(8)]
    explainer = ModelExplainer(
        model=trained_model,
        method="anchor",
        feature_names=feature_names
    )

    # Anchor requires categorical features list
    categorical_features = [3, 4, 5]  # Indices of categorical features
    explainer.fit(background_data, categorical_features=categorical_features)

    assert explainer.explainer is not None


@patch('risk_churn_platform.explainers.model_explainer.AnchorTabular')
def test_explainer_explain_anchor(
    mock_anchor: MagicMock,
    trained_model: RiskScorerV1,
    background_data: NDArray[np.float64],
    test_data: NDArray[np.float64]
) -> None:
    """Test generating Anchor explanations."""
    # Mock the Anchor explainer
    mock_instance = MagicMock()
    mock_anchor.return_value = mock_instance

    # Mock explanation result
    mock_explanation = MagicMock()
    mock_explanation.anchor = ["feature_0 > 0.5", "feature_1 < 0.3"]
    mock_explanation.precision = 0.95
    mock_explanation.coverage = 0.30
    mock_instance.explain.return_value = mock_explanation

    feature_names = [f"feature_{i}" for i in range(8)]
    explainer = ModelExplainer(
        model=trained_model,
        method="anchor",
        feature_names=feature_names
    )
    explainer.fit(background_data, categorical_features=[])

    explanations = explainer.explain(test_data[:1], threshold=0.95)

    assert explanations["method"] == "anchor"
    assert "explanations" in explanations
    assert len(explanations["explanations"]) == 1

    # Check explanation structure
    first_exp = explanations["explanations"][0]
    assert "anchor_rule" in first_exp
    assert "precision" in first_exp
    assert "coverage" in first_exp


def test_seldon_explainer_initialization() -> None:
    """Test Seldon explainer wrapper initialization."""
    mock_explainer = MagicMock(spec=ModelExplainer)
    seldon_explainer = SeldonExplainer(explainer=mock_explainer)

    assert seldon_explainer.explainer == mock_explainer
    assert seldon_explainer.ready is False


def test_seldon_explainer_load() -> None:
    """Test loading Seldon explainer."""
    mock_explainer = MagicMock(spec=ModelExplainer)
    seldon_explainer = SeldonExplainer(explainer=mock_explainer)

    result = seldon_explainer.load()

    assert result is True
    assert seldon_explainer.ready is True


def test_seldon_explainer_explain() -> None:
    """Test Seldon explainer explain method."""
    mock_explainer = MagicMock(spec=ModelExplainer)
    mock_explainer.explain.return_value = {
        "method": "shap",
        "explanations": []
    }

    seldon_explainer = SeldonExplainer(explainer=mock_explainer)
    seldon_explainer.load()

    test_data = np.random.randn(5, 8)
    result = seldon_explainer.explain(test_data)

    assert result["method"] == "shap"
    mock_explainer.explain.assert_called_once_with(test_data)


def test_seldon_explainer_health_status() -> None:
    """Test Seldon explainer health status."""
    mock_explainer = MagicMock(spec=ModelExplainer)
    seldon_explainer = SeldonExplainer(explainer=mock_explainer)

    # Before load
    status = seldon_explainer.health_status()
    assert status["ready"] is False

    # After load
    seldon_explainer.load()
    status = seldon_explainer.health_status()
    assert status["ready"] is True
