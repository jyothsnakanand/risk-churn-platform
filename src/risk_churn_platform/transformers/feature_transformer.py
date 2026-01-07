"""Feature transformation pipeline for risk/churn scoring."""

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.preprocessing import LabelEncoder, StandardScaler


class FeatureTransformer:
    """Transform raw input data into model-ready features."""

    def __init__(self, feature_names: List[str]) -> None:
        """Initialize the feature transformer.

        Args:
            feature_names: List of expected feature names
        """
        self.feature_names = feature_names
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.categorical_features = ["favorite_category", "payment_method", "shipping_method"]
        self.numerical_features = [
            "customer_age_days",
            "account_age_days",
            "total_orders",
            "total_revenue",
            "avg_order_value",
            "days_since_last_order",
            "order_frequency",
            "website_visits_30d",
            "email_open_rate",
            "cart_abandonment_rate",
            "product_views_30d",
            "support_tickets_total",
            "support_tickets_open",
            "returns_count",
            "refunds_count",
            "discount_usage_rate",
            "premium_product_rate",
            "failed_payment_count",
        ]
        self.fitted = False

    def fit(self, X: pd.DataFrame) -> "FeatureTransformer":
        """Fit the transformer on training data.

        Args:
            X: Training data

        Returns:
            Self for method chaining
        """
        # Fit label encoders for categorical features
        for col in self.categorical_features:
            if col in X.columns:
                le = LabelEncoder()
                le.fit(X[col].astype(str))
                self.label_encoders[col] = le

        # Transform categorical features
        X_transformed = self._encode_categoricals(X.copy())

        # Fit scaler on numerical features
        numerical_cols = [col for col in self.numerical_features if col in X_transformed.columns]
        if numerical_cols:
            self.scaler.fit(X_transformed[numerical_cols])

        self.fitted = True
        return self

    def transform(self, X: pd.DataFrame | Dict[str, Any]) -> NDArray[np.float64]:
        """Transform input data into model-ready features.

        Args:
            X: Input data as DataFrame or dictionary

        Returns:
            Transformed features as numpy array
        """
        if not self.fitted:
            raise ValueError("Transformer not fitted. Call fit() first.")

        # Convert dict to DataFrame if necessary
        if isinstance(X, dict):
            X = pd.DataFrame([X])

        # Ensure all required features are present
        missing_features = set(self.feature_names) - set(X.columns)
        if missing_features:
            raise ValueError(f"Missing features: {missing_features}")

        # Transform categorical features
        X_transformed = self._encode_categoricals(X.copy())

        # Scale numerical features
        numerical_cols = [col for col in self.numerical_features if col in X_transformed.columns]
        if numerical_cols:
            X_transformed[numerical_cols] = self.scaler.transform(X_transformed[numerical_cols])

        # Select and order features
        X_final = X_transformed[self.feature_names]

        return X_final.values

    def fit_transform(self, X: pd.DataFrame) -> NDArray[np.float64]:
        """Fit and transform in one step.

        Args:
            X: Input data

        Returns:
            Transformed features as numpy array
        """
        self.fit(X)
        return self.transform(X)

    def _encode_categoricals(self, X: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features.

        Args:
            X: Input DataFrame

        Returns:
            DataFrame with encoded categorical features
        """
        for col in self.categorical_features:
            if col in X.columns and col in self.label_encoders:
                # Handle unseen categories
                X[col] = X[col].astype(str)
                le = self.label_encoders[col]
                X[col] = X[col].apply(
                    lambda x: le.transform([x])[0] if x in le.classes_ else -1
                )

        return X


class SeldonTransformer:
    """Seldon-compatible transformer wrapper."""

    def __init__(self, transformer: FeatureTransformer) -> None:
        """Initialize Seldon transformer wrapper.

        Args:
            transformer: Feature transformer instance
        """
        self.transformer = transformer
        self.ready = False

    def load(self) -> bool:
        """Load the transformer.

        Returns:
            True if transformer loaded successfully
        """
        # In production, you would load fitted transformer from disk
        self.ready = True
        return True

    def transform_input(
        self, X: NDArray[np.float64], feature_names: List[str] | None = None
    ) -> NDArray[np.float64]:
        """Transform input data.

        Args:
            X: Input data
            feature_names: Feature names

        Returns:
            Transformed data
        """
        if feature_names:
            # Convert to DataFrame for named access
            df = pd.DataFrame(X, columns=feature_names)
            return self.transformer.transform(df)
        return X

    def health_status(self) -> Dict[str, bool]:
        """Return health status.

        Returns:
            Health status dictionary
        """
        return {"ready": self.ready}
