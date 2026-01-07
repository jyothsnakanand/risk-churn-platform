"""Unit tests for feature transformer."""

import numpy as np
import pandas as pd
import pytest
from numpy.typing import NDArray

from risk_churn_platform.transformers.feature_transformer import FeatureTransformer


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Generate sample DataFrame for testing.

    Returns:
        Sample DataFrame with features
    """
    return pd.DataFrame({
        'customer_tenure': [12, 24, 36],
        'monthly_charges': [50.0, 75.0, 100.0],
        'total_charges': [600.0, 1800.0, 3600.0],
        'contract_type': ['Month-to-month', 'One year', 'Two year'],
        'payment_method': ['Credit card', 'Bank transfer', 'Electronic check'],
        'internet_service': ['DSL', 'Fiber optic', 'No'],
        'support_tickets': [1, 2, 0],
        'login_frequency': [3.5, 5.2, 2.1],
    })


@pytest.fixture
def feature_names() -> list[str]:
    """Get feature names.

    Returns:
        List of feature names
    """
    return [
        'customer_tenure', 'monthly_charges', 'total_charges',
        'contract_type', 'payment_method', 'internet_service',
        'support_tickets', 'login_frequency'
    ]


def test_transformer_fit_transform(
    sample_dataframe: pd.DataFrame, feature_names: list[str]
) -> None:
    """Test fitting and transforming data."""
    transformer = FeatureTransformer(feature_names)

    # Fit and transform
    X_transformed = transformer.fit_transform(sample_dataframe)

    # Check output shape
    assert X_transformed.shape == (3, 8)
    assert transformer.fitted

    # Check that scaling was applied
    assert X_transformed.dtype == np.float64


def test_transformer_transform_dict(feature_names: list[str]) -> None:
    """Test transforming dictionary input."""
    # Create training data
    train_df = pd.DataFrame({
        'customer_tenure': [12, 24, 36, 48],
        'monthly_charges': [50.0, 75.0, 100.0, 125.0],
        'total_charges': [600.0, 1800.0, 3600.0, 6000.0],
        'contract_type': ['Month-to-month', 'One year', 'Two year', 'One year'],
        'payment_method': ['Credit card', 'Bank transfer', 'Electronic check', 'Credit card'],
        'internet_service': ['DSL', 'Fiber optic', 'No', 'Fiber optic'],
        'support_tickets': [1, 2, 0, 3],
        'login_frequency': [3.5, 5.2, 2.1, 4.8],
    })

    transformer = FeatureTransformer(feature_names)
    transformer.fit(train_df)

    # Transform dictionary
    input_dict = {
        'customer_tenure': 30,
        'monthly_charges': 80.0,
        'total_charges': 2400.0,
        'contract_type': 'One year',
        'payment_method': 'Credit card',
        'internet_service': 'DSL',
        'support_tickets': 1,
        'login_frequency': 4.0,
    }

    X_transformed = transformer.transform(input_dict)

    assert X_transformed.shape == (1, 8)
    assert isinstance(X_transformed, np.ndarray)


def test_transformer_not_fitted_error(feature_names: list[str]) -> None:
    """Test error when transformer not fitted."""
    transformer = FeatureTransformer(feature_names)

    test_data = pd.DataFrame({
        'customer_tenure': [12],
        'monthly_charges': [50.0],
        'total_charges': [600.0],
        'contract_type': ['Month-to-month'],
        'payment_method': ['Credit card'],
        'internet_service': ['DSL'],
        'support_tickets': [1],
        'login_frequency': [3.5],
    })

    with pytest.raises(ValueError, match="Transformer not fitted"):
        transformer.transform(test_data)


def test_transformer_missing_features(
    sample_dataframe: pd.DataFrame, feature_names: list[str]
) -> None:
    """Test error when required features are missing."""
    transformer = FeatureTransformer(feature_names)
    transformer.fit(sample_dataframe)

    # Create data with missing feature
    incomplete_data = pd.DataFrame({
        'customer_tenure': [12],
        'monthly_charges': [50.0],
        # Missing other features
    })

    with pytest.raises(ValueError, match="Missing features"):
        transformer.transform(incomplete_data)


def test_transformer_unseen_categories(
    sample_dataframe: pd.DataFrame, feature_names: list[str]
) -> None:
    """Test handling of unseen categorical values."""
    transformer = FeatureTransformer(feature_names)
    transformer.fit(sample_dataframe)

    # Create data with unseen category
    test_data = pd.DataFrame({
        'customer_tenure': [12],
        'monthly_charges': [50.0],
        'total_charges': [600.0],
        'contract_type': ['Unknown contract'],  # Unseen
        'payment_method': ['Credit card'],
        'internet_service': ['DSL'],
        'support_tickets': [1],
        'login_frequency': [3.5],
    })

    # Should handle gracefully (encode as -1)
    X_transformed = transformer.transform(test_data)
    assert X_transformed.shape == (1, 8)
