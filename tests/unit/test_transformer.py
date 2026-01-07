"""Unit tests for feature transformer."""

import numpy as np
import pandas as pd
import pytest

from risk_churn_platform.transformers.feature_transformer import FeatureTransformer


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Generate sample DataFrame for testing.

    Returns:
        Sample DataFrame with all 21 e-commerce features
    """
    return pd.DataFrame(
        {
            # Customer Demographics & Tenure
            "customer_age_days": [365, 730, 1095],
            "account_age_days": [365, 730, 1095],
            # Purchase Behavior
            "total_orders": [5, 10, 20],
            "total_revenue": [250.0, 500.0, 1000.0],
            "avg_order_value": [50.0, 50.0, 50.0],
            "days_since_last_order": [10, 20, 30],
            "order_frequency": [0.5, 1.0, 1.5],
            # Engagement Metrics
            "website_visits_30d": [5, 10, 15],
            "email_open_rate": [0.5, 0.6, 0.7],
            "cart_abandonment_rate": [0.3, 0.4, 0.5],
            "product_views_30d": [10, 20, 30],
            # Customer Service
            "support_tickets_total": [1, 2, 3],
            "support_tickets_open": [0, 1, 0],
            "returns_count": [0, 1, 2],
            "refunds_count": [0, 0, 1],
            # Product Preferences
            "favorite_category": ["Fashion", "Electronics", "Home"],
            "discount_usage_rate": [0.3, 0.5, 0.7],
            "premium_product_rate": [0.2, 0.4, 0.6],
            # Payment & Shipping
            "payment_method": ["Credit Card", "PayPal", "Debit Card"],
            "shipping_method": ["Standard", "Express", "Next Day"],
            "failed_payment_count": [0, 1, 0],
        }
    )


@pytest.fixture
def feature_names() -> list[str]:
    """Get feature names.

    Returns:
        List of all 21 e-commerce feature names
    """
    return [
        # Customer Demographics & Tenure
        "customer_age_days",
        "account_age_days",
        # Purchase Behavior
        "total_orders",
        "total_revenue",
        "avg_order_value",
        "days_since_last_order",
        "order_frequency",
        # Engagement Metrics
        "website_visits_30d",
        "email_open_rate",
        "cart_abandonment_rate",
        "product_views_30d",
        # Customer Service
        "support_tickets_total",
        "support_tickets_open",
        "returns_count",
        "refunds_count",
        # Product Preferences
        "favorite_category",
        "discount_usage_rate",
        "premium_product_rate",
        # Payment & Shipping
        "payment_method",
        "shipping_method",
        "failed_payment_count",
    ]


def test_transformer_fit_transform(
    sample_dataframe: pd.DataFrame, feature_names: list[str]
) -> None:
    """Test fitting and transforming data."""
    transformer = FeatureTransformer(feature_names)

    # Fit and transform
    X_transformed = transformer.fit_transform(sample_dataframe)

    # Check output shape (3 samples, 21 features)
    assert X_transformed.shape == (3, 21)
    assert transformer.fitted

    # Check that scaling was applied
    assert X_transformed.dtype == np.float64


def test_transformer_transform_dict(feature_names: list[str]) -> None:
    """Test transforming dictionary input."""
    # Create training data with all 21 features
    train_df = pd.DataFrame(
        {
            "customer_age_days": [365, 730, 1095, 1460],
            "account_age_days": [365, 730, 1095, 1460],
            "total_orders": [5, 10, 15, 20],
            "total_revenue": [250.0, 500.0, 750.0, 1000.0],
            "avg_order_value": [50.0, 50.0, 50.0, 50.0],
            "days_since_last_order": [10, 20, 30, 40],
            "order_frequency": [0.5, 1.0, 1.5, 2.0],
            "website_visits_30d": [5, 10, 15, 20],
            "email_open_rate": [0.5, 0.6, 0.7, 0.8],
            "cart_abandonment_rate": [0.3, 0.4, 0.5, 0.6],
            "product_views_30d": [10, 20, 30, 40],
            "support_tickets_total": [1, 2, 3, 4],
            "support_tickets_open": [0, 1, 0, 1],
            "returns_count": [0, 1, 2, 3],
            "refunds_count": [0, 0, 1, 1],
            "favorite_category": ["Fashion", "Electronics", "Home", "Electronics"],
            "discount_usage_rate": [0.3, 0.5, 0.7, 0.9],
            "premium_product_rate": [0.2, 0.4, 0.6, 0.8],
            "payment_method": ["Credit Card", "PayPal", "Debit Card", "Credit Card"],
            "shipping_method": ["Standard", "Express", "Next Day", "Express"],
            "failed_payment_count": [0, 1, 0, 2],
        }
    )

    transformer = FeatureTransformer(feature_names)
    transformer.fit(train_df)

    # Transform dictionary with all 21 features
    input_dict = {
        "customer_age_days": 500,
        "account_age_days": 500,
        "total_orders": 12,
        "total_revenue": 600.0,
        "avg_order_value": 50.0,
        "days_since_last_order": 15,
        "order_frequency": 1.2,
        "website_visits_30d": 8,
        "email_open_rate": 0.65,
        "cart_abandonment_rate": 0.35,
        "product_views_30d": 25,
        "support_tickets_total": 2,
        "support_tickets_open": 0,
        "returns_count": 1,
        "refunds_count": 0,
        "favorite_category": "Electronics",
        "discount_usage_rate": 0.4,
        "premium_product_rate": 0.5,
        "payment_method": "Credit Card",
        "shipping_method": "Standard",
        "failed_payment_count": 0,
    }

    X_transformed = transformer.transform(input_dict)

    assert X_transformed.shape == (1, 21)
    assert isinstance(X_transformed, np.ndarray)


def test_transformer_not_fitted_error(feature_names: list[str]) -> None:
    """Test error when transformer not fitted."""
    transformer = FeatureTransformer(feature_names)

    test_data = pd.DataFrame(
        {
            "customer_age_days": [365],
            "account_age_days": [365],
            "total_orders": [10],
            "total_revenue": [500.0],
            "avg_order_value": [50.0],
            "days_since_last_order": [15],
            "order_frequency": [1.0],
            "website_visits_30d": [10],
            "email_open_rate": [0.6],
            "cart_abandonment_rate": [0.4],
            "product_views_30d": [20],
            "support_tickets_total": [2],
            "support_tickets_open": [0],
            "returns_count": [1],
            "refunds_count": [0],
            "favorite_category": ["Fashion"],
            "discount_usage_rate": [0.5],
            "premium_product_rate": [0.4],
            "payment_method": ["Credit Card"],
            "shipping_method": ["Standard"],
            "failed_payment_count": [0],
        }
    )

    with pytest.raises(ValueError, match="Transformer not fitted"):
        transformer.transform(test_data)


def test_transformer_missing_features(
    sample_dataframe: pd.DataFrame, feature_names: list[str]
) -> None:
    """Test error when required features are missing."""
    transformer = FeatureTransformer(feature_names)
    transformer.fit(sample_dataframe)

    # Create data with missing feature
    incomplete_data = pd.DataFrame(
        {
            "customer_age_days": [12],
            "total_revenue": [50.0],
            # Missing other features
        }
    )

    with pytest.raises(ValueError, match="Missing features"):
        transformer.transform(incomplete_data)


def test_transformer_unseen_categories(
    sample_dataframe: pd.DataFrame, feature_names: list[str]
) -> None:
    """Test handling of unseen categorical values."""
    transformer = FeatureTransformer(feature_names)
    transformer.fit(sample_dataframe)

    # Create data with unseen category
    test_data = pd.DataFrame(
        {
            "customer_age_days": [365],
            "account_age_days": [365],
            "total_orders": [10],
            "total_revenue": [500.0],
            "avg_order_value": [50.0],
            "days_since_last_order": [15],
            "order_frequency": [1.0],
            "website_visits_30d": [10],
            "email_open_rate": [0.6],
            "cart_abandonment_rate": [0.4],
            "product_views_30d": [20],
            "support_tickets_total": [2],
            "support_tickets_open": [0],
            "returns_count": [1],
            "refunds_count": [0],
            "favorite_category": ["Unknown Category"],  # Unseen category
            "discount_usage_rate": [0.5],
            "premium_product_rate": [0.4],
            "payment_method": ["Credit Card"],
            "shipping_method": ["Standard"],
            "failed_payment_count": [0],
        }
    )

    # Should handle gracefully (encode as -1)
    X_transformed = transformer.transform(test_data)
    assert X_transformed.shape == (1, 21)
