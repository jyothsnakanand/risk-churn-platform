"""E-commerce customer churn training example.

This script demonstrates how to train the churn prediction models
using e-commerce customer data.
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from risk_churn_platform.models.risk_scorer import RiskScorerV1, RiskScorerV2
from risk_churn_platform.transformers.feature_transformer import FeatureTransformer


def generate_ecommerce_data(n_samples: int = 10000) -> pd.DataFrame:
    """Generate synthetic e-commerce customer data.

    Args:
        n_samples: Number of samples to generate

    Returns:
        DataFrame with e-commerce features and churn labels
    """
    np.random.seed(42)

    # Simulate realistic e-commerce customer behavior
    data = {
        # Customer Demographics & Tenure
        'customer_age_days': np.random.randint(1, 1825, n_samples),  # 0-5 years
        'account_age_days': np.random.randint(1, 2000, n_samples),

        # Purchase Behavior
        'total_orders': np.random.poisson(15, n_samples),
        'total_revenue': np.random.lognormal(5, 1.5, n_samples),  # Skewed distribution
        'avg_order_value': np.random.lognormal(3.5, 0.8, n_samples),
        'days_since_last_order': np.random.exponential(30, n_samples).astype(int),
        'order_frequency': np.random.gamma(2, 1.5, n_samples),

        # Engagement Metrics
        'website_visits_30d': np.random.poisson(8, n_samples),
        'email_open_rate': np.random.beta(2, 5, n_samples),  # Typically low open rates
        'cart_abandonment_rate': np.random.beta(3, 2, n_samples),  # Higher abandonment
        'product_views_30d': np.random.poisson(25, n_samples),

        # Customer Service
        'support_tickets_total': np.random.poisson(2, n_samples),
        'support_tickets_open': np.random.binomial(3, 0.2, n_samples),
        'returns_count': np.random.poisson(1, n_samples),
        'refunds_count': np.random.poisson(0.5, n_samples),

        # Product Preferences
        'favorite_category': np.random.choice(
            ['Electronics', 'Fashion', 'Home', 'Beauty', 'Sports'],
            n_samples
        ),
        'discount_usage_rate': np.random.beta(2, 3, n_samples),
        'premium_product_rate': np.random.beta(2, 8, n_samples),  # Most buy regular products

        # Payment & Shipping
        'payment_method': np.random.choice(
            ['Credit Card', 'Debit Card', 'PayPal', 'Apple Pay', 'Buy Now Pay Later'],
            n_samples,
            p=[0.35, 0.20, 0.25, 0.15, 0.05]
        ),
        'shipping_method': np.random.choice(
            ['Standard', 'Express', 'Next Day'],
            n_samples,
            p=[0.70, 0.20, 0.10]
        ),
        'failed_payment_count': np.random.poisson(0.3, n_samples),
    }

    df = pd.DataFrame(data)

    # Create churn label based on realistic business logic
    # Churn is more likely when:
    # - Long time since last order
    # - Low engagement
    # - High cart abandonment
    # - Multiple returns/refunds
    # - Failed payments

    churn_score = (
        (df['days_since_last_order'] > 90).astype(int) * 0.3 +
        (df['website_visits_30d'] < 3).astype(int) * 0.2 +
        (df['cart_abandonment_rate'] > 0.7).astype(int) * 0.15 +
        (df['returns_count'] > 3).astype(int) * 0.1 +
        (df['support_tickets_open'] > 1).astype(int) * 0.1 +
        (df['failed_payment_count'] > 1).astype(int) * 0.15
    )

    # Add some randomness
    churn_score += np.random.normal(0, 0.1, n_samples)

    # Convert to binary label
    df['label'] = (churn_score > 0.5).astype(int)

    print(f"\nGenerated {n_samples} e-commerce customer records")
    print(f"Churn rate: {df['label'].mean():.2%}")
    print(f"\nFeature summary:")
    print(f"  - Avg customer age: {df['customer_age_days'].mean():.0f} days ({df['customer_age_days'].mean()/365:.1f} years)")
    print(f"  - Avg total orders: {df['total_orders'].mean():.1f}")
    print(f"  - Avg lifetime value: ${df['total_revenue'].mean():.2f}")
    print(f"  - Avg days since last order: {df['days_since_last_order'].mean():.0f}")
    print(f"  - Avg email open rate: {df['email_open_rate'].mean():.1%}")

    return df


def main():
    """Main training pipeline."""
    print("=" * 70)
    print("E-COMMERCE CUSTOMER CHURN PREDICTION - MODEL TRAINING")
    print("=" * 70)

    # Create model directories
    os.makedirs('models/v1', exist_ok=True)
    os.makedirs('models/v2', exist_ok=True)

    # Generate data
    print("\n[1/5] Generating synthetic e-commerce data...")
    data = generate_ecommerce_data(n_samples=15000)

    # Define features
    feature_names = [
        'customer_age_days', 'account_age_days',
        'total_orders', 'total_revenue', 'avg_order_value',
        'days_since_last_order', 'order_frequency',
        'website_visits_30d', 'email_open_rate', 'cart_abandonment_rate',
        'product_views_30d', 'support_tickets_total', 'support_tickets_open',
        'returns_count', 'refunds_count', 'favorite_category',
        'discount_usage_rate', 'premium_product_rate',
        'payment_method', 'shipping_method', 'failed_payment_count'
    ]

    # Split data
    print("\n[2/5] Splitting data into train/validation/test sets...")
    X = data[feature_names]
    y = data['label']

    # 60% train, 20% validation, 20% test
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.4, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )

    print(f"  - Training set: {len(X_train)} samples")
    print(f"  - Validation set: {len(X_val)} samples")
    print(f"  - Test set: {len(X_test)} samples")

    # Initialize and fit transformer
    print("\n[3/5] Fitting feature transformer...")
    transformer = FeatureTransformer(feature_names)
    X_train_transformed = transformer.fit_transform(X_train)
    X_val_transformed = transformer.transform(X_val)
    X_test_transformed = transformer.transform(X_test)
    print(f"  - Transformed features shape: {X_train_transformed.shape}")

    # Train Model V1 (Random Forest)
    print("\n[4/5] Training Model V1 (Random Forest)...")
    model_v1 = RiskScorerV1()
    model_v1.train(X_train_transformed, y_train.values, n_estimators=100, max_depth=10)

    # Evaluate V1
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

    y_val_pred_v1 = model_v1.predict(X_val_transformed)
    y_val_proba_v1 = model_v1.predict_proba(X_val_transformed)[:, 1]

    print(f"\n  Model V1 Performance (Validation Set):")
    print(f"    Accuracy:  {accuracy_score(y_val, y_val_pred_v1):.3f}")
    print(f"    Precision: {precision_score(y_val, y_val_pred_v1):.3f}")
    print(f"    Recall:    {recall_score(y_val, y_val_pred_v1):.3f}")
    print(f"    F1 Score:  {f1_score(y_val, y_val_pred_v1):.3f}")
    print(f"    ROC AUC:   {roc_auc_score(y_val, y_val_proba_v1):.3f}")

    model_v1.save('models/v1/model.pkl')
    print(f"  ✓ Model V1 saved to models/v1/model.pkl")

    # Save transformer
    import pickle
    with open('models/transformer.pkl', 'wb') as f:
        pickle.dump(transformer, f)
    print(f"  ✓ Transformer saved to models/transformer.pkl")

    # Train Model V2 (Gradient Boosting)
    print("\n[5/5] Training Model V2 (Gradient Boosting)...")
    model_v2 = RiskScorerV2()
    model_v2.train(X_train_transformed, y_train.values, n_estimators=150, learning_rate=0.1)

    # Evaluate V2
    y_val_pred_v2 = model_v2.predict(X_val_transformed)
    y_val_proba_v2 = model_v2.predict_proba(X_val_transformed)[:, 1]

    print(f"\n  Model V2 Performance (Validation Set):")
    print(f"    Accuracy:  {accuracy_score(y_val, y_val_pred_v2):.3f}")
    print(f"    Precision: {precision_score(y_val, y_val_pred_v2):.3f}")
    print(f"    Recall:    {recall_score(y_val, y_val_pred_v2):.3f}")
    print(f"    F1 Score:  {f1_score(y_val, y_val_pred_v2):.3f}")
    print(f"    ROC AUC:   {roc_auc_score(y_val, y_val_proba_v2):.3f}")

    model_v2.save('models/v2/model.pkl')
    print(f"  ✓ Model V2 saved to models/v2/model.pkl")

    # Test set evaluation
    print("\n" + "=" * 70)
    print("FINAL TEST SET EVALUATION")
    print("=" * 70)

    y_test_pred_v1 = model_v1.predict(X_test_transformed)
    y_test_proba_v1 = model_v1.predict_proba(X_test_transformed)[:, 1]

    y_test_pred_v2 = model_v2.predict(X_test_transformed)
    y_test_proba_v2 = model_v2.predict_proba(X_test_transformed)[:, 1]

    print(f"\nModel V1 (Random Forest) - Test Set:")
    print(f"  Accuracy:  {accuracy_score(y_test, y_test_pred_v1):.3f}")
    print(f"  F1 Score:  {f1_score(y_test, y_test_pred_v1):.3f}")
    print(f"  ROC AUC:   {roc_auc_score(y_test, y_test_proba_v1):.3f}")

    print(f"\nModel V2 (Gradient Boosting) - Test Set:")
    print(f"  Accuracy:  {accuracy_score(y_test, y_test_pred_v2):.3f}")
    print(f"  F1 Score:  {f1_score(y_test, y_test_pred_v2):.3f}")
    print(f"  ROC AUC:   {roc_auc_score(y_test, y_test_proba_v2):.3f}")

    print("\n" + "=" * 70)
    print("✓ TRAINING COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Start the API server: uvicorn src.risk_churn_platform.api.rest_api:app --reload")
    print("2. Make predictions using the example in examples/ecommerce_prediction_example.py")
    print("3. View API docs at http://localhost:8080/docs")


if __name__ == "__main__":
    main()
