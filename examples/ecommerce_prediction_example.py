"""E-commerce customer churn prediction example.

This script demonstrates how to make churn predictions for e-commerce customers.
"""

import requests
import json


def predict_churn(customer_data: dict) -> dict:
    """Make a churn prediction for a customer.

    Args:
        customer_data: Customer features dictionary

    Returns:
        Prediction response
    """
    response = requests.post(
        'http://127.0.0.1:8080/predict',
        json=customer_data
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Prediction failed: {response.text}")


def main():
    """Run prediction examples."""
    print("=" * 70)
    print("E-COMMERCE CUSTOMER CHURN PREDICTION - EXAMPLES")
    print("=" * 70)

    # Example 1: High-risk customer (likely to churn)
    print("\n[Example 1] High-Risk Customer Profile")
    print("-" * 70)

    high_risk_customer = {
        # Customer Demographics & Tenure
        "customer_age_days": 730,  # 2 years old customer
        "account_age_days": 750,

        # Purchase Behavior - RED FLAGS
        "total_orders": 3,  # Very few orders
        "total_revenue": 150.00,  # Low lifetime value
        "avg_order_value": 50.00,
        "days_since_last_order": 180,  # 6 months inactive!
        "order_frequency": 0.1,  # Barely ordering

        # Engagement Metrics - RED FLAGS
        "website_visits_30d": 1,  # Almost no engagement
        "email_open_rate": 0.05,  # Not opening emails
        "cart_abandonment_rate": 0.85,  # High abandonment
        "product_views_30d": 2,

        # Customer Service - RED FLAGS
        "support_tickets_total": 5,  # Many complaints
        "support_tickets_open": 2,  # Unresolved issues
        "returns_count": 3,  # Lots of returns
        "refunds_count": 2,

        # Product Preferences
        "favorite_category": "Electronics",
        "discount_usage_rate": 0.90,  # Only buys on deep discount
        "premium_product_rate": 0.0,

        # Payment & Shipping
        "payment_method": "Credit Card",
        "shipping_method": "Standard",
        "failed_payment_count": 2  # Payment issues
    }

    print("Customer Profile:")
    print(f"  - Customer age: {high_risk_customer['customer_age_days']/365:.1f} years")
    print(f"  - Total orders: {high_risk_customer['total_orders']}")
    print(f"  - Lifetime value: ${high_risk_customer['total_revenue']:.2f}")
    print(f"  - Days since last order: {high_risk_customer['days_since_last_order']}")
    print(f"  - Email open rate: {high_risk_customer['email_open_rate']:.1%}")
    print(f"  - Open support tickets: {high_risk_customer['support_tickets_open']}")

    result = predict_churn(high_risk_customer)

    print(f"\nPrediction Result:")
    print(f"  ⚠️  Churn Risk Score: {result['risk_score']:.1f}%")
    print(f"  📊 Churn Probability: {result['churn_probability']:.1%}")
    print(f"  🤖 Model Version: {result['model_version']}")
    print(f"  ⚡ Latency: {result['latency_ms']:.2f}ms")

    if result['risk_score'] > 70:
        print(f"\n  🚨 HIGH RISK - Immediate intervention needed!")
        print(f"     Recommended actions:")
        print(f"     - Send personalized win-back campaign")
        print(f"     - Offer special discount or loyalty bonus")
        print(f"     - Resolve open support tickets")
        print(f"     - Contact customer directly")

    # Example 2: Low-risk customer (engaged and loyal)
    print("\n\n[Example 2] Low-Risk Customer Profile")
    print("-" * 70)

    low_risk_customer = {
        # Customer Demographics & Tenure
        "customer_age_days": 1095,  # 3 years loyal customer
        "account_age_days": 1100,

        # Purchase Behavior - HEALTHY
        "total_orders": 45,  # Regular purchaser
        "total_revenue": 2850.00,  # High lifetime value
        "avg_order_value": 63.33,
        "days_since_last_order": 12,  # Recent purchase
        "order_frequency": 1.25,  # More than 1 per month

        # Engagement Metrics - EXCELLENT
        "website_visits_30d": 15,  # Highly engaged
        "email_open_rate": 0.65,  # Opens emails
        "cart_abandonment_rate": 0.25,  # Low abandonment
        "product_views_30d": 50,

        # Customer Service - MINIMAL ISSUES
        "support_tickets_total": 2,
        "support_tickets_open": 0,
        "returns_count": 1,
        "refunds_count": 0,

        # Product Preferences
        "favorite_category": "Fashion",
        "discount_usage_rate": 0.30,  # Doesn't need discounts
        "premium_product_rate": 0.40,  # Buys quality items

        # Payment & Shipping
        "payment_method": "Credit Card",
        "shipping_method": "Express",
        "failed_payment_count": 0
    }

    print("Customer Profile:")
    print(f"  - Customer age: {low_risk_customer['customer_age_days']/365:.1f} years")
    print(f"  - Total orders: {low_risk_customer['total_orders']}")
    print(f"  - Lifetime value: ${low_risk_customer['total_revenue']:.2f}")
    print(f"  - Days since last order: {low_risk_customer['days_since_last_order']}")
    print(f"  - Email open rate: {low_risk_customer['email_open_rate']:.1%}")
    print(f"  - Open support tickets: {low_risk_customer['support_tickets_open']}")

    result = predict_churn(low_risk_customer)

    print(f"\nPrediction Result:")
    print(f"  ✅ Churn Risk Score: {result['risk_score']:.1f}%")
    print(f"  📊 Churn Probability: {result['churn_probability']:.1%}")
    print(f"  🤖 Model Version: {result['model_version']}")
    print(f"  ⚡ Latency: {result['latency_ms']:.2f}ms")

    if result['risk_score'] < 30:
        print(f"\n  ✅ LOW RISK - Customer is engaged and loyal!")
        print(f"     Recommended actions:")
        print(f"     - Maintain regular communication")
        print(f"     - Offer VIP/loyalty program")
        print(f"     - Request reviews and referrals")
        print(f"     - Provide early access to new products")

    # Example 3: Medium-risk customer
    print("\n\n[Example 3] Medium-Risk Customer Profile")
    print("-" * 70)

    medium_risk_customer = {
        "customer_age_days": 540,  # 1.5 years
        "account_age_days": 550,
        "total_orders": 12,
        "total_revenue": 720.00,
        "avg_order_value": 60.00,
        "days_since_last_order": 45,  # Slightly concerning
        "order_frequency": 0.67,
        "website_visits_30d": 5,
        "email_open_rate": 0.35,
        "cart_abandonment_rate": 0.50,
        "product_views_30d": 15,
        "support_tickets_total": 3,
        "support_tickets_open": 1,
        "returns_count": 2,
        "refunds_count": 1,
        "favorite_category": "Home",
        "discount_usage_rate": 0.55,
        "premium_product_rate": 0.20,
        "payment_method": "PayPal",
        "shipping_method": "Standard",
        "failed_payment_count": 1
    }

    print("Customer Profile:")
    print(f"  - Customer age: {medium_risk_customer['customer_age_days']/365:.1f} years")
    print(f"  - Total orders: {medium_risk_customer['total_orders']}")
    print(f"  - Lifetime value: ${medium_risk_customer['total_revenue']:.2f}")
    print(f"  - Days since last order: {medium_risk_customer['days_since_last_order']}")

    result = predict_churn(medium_risk_customer)

    print(f"\nPrediction Result:")
    print(f"  ⚡ Churn Risk Score: {result['risk_score']:.1f}%")
    print(f"  📊 Churn Probability: {result['churn_probability']:.1%}")
    print(f"  🤖 Model Version: {result['model_version']}")

    if 30 <= result['risk_score'] <= 70:
        print(f"\n  ⚠️  MEDIUM RISK - Preventive action recommended")
        print(f"     Recommended actions:")
        print(f"     - Send re-engagement email campaign")
        print(f"     - Offer targeted discount on favorite category")
        print(f"     - Resolve open support ticket")
        print(f"     - Improve email content relevance")

    print("\n" + "=" * 70)
    print("PREDICTION EXAMPLES COMPLETE")
    print("=" * 70)
    print("\nView detailed API documentation at: http://localhost:8080/docs")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API server")
        print("Please ensure the API server is running:")
        print("  uvicorn src.risk_churn_platform.api.rest_api:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
