"""Load testing with Locust.

Run with:
    locust -f tests/load/locustfile.py --host=http://localhost:8080
"""

import random
import time
from typing import Any, Dict

from locust import HttpUser, between, task


class MLPlatformUser(HttpUser):
    """Simulated user for load testing."""

    # Wait 1-3 seconds between requests
    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Initialize user session."""
        # Get or set API key
        self.api_key = "sk_test_your_api_key_here"  # Replace with actual key
        self.headers = {"X-API-Key": self.api_key}

    def generate_customer_data(self) -> Dict[str, Any]:
        """Generate realistic customer data.

        Returns:
            Customer feature dictionary
        """
        return {
            # Customer Demographics
            "customer_age_days": random.randint(30, 1825),
            "account_age_days": random.randint(30, 1825),
            # Purchase Behavior
            "total_orders": random.randint(1, 100),
            "total_revenue": round(random.uniform(50, 5000), 2),
            "avg_order_value": round(random.uniform(20, 200), 2),
            "days_since_last_order": random.randint(0, 365),
            "order_frequency": round(random.uniform(0.1, 5.0), 2),
            # Engagement
            "website_visits_30d": random.randint(0, 50),
            "email_open_rate": round(random.uniform(0, 1), 2),
            "cart_abandonment_rate": round(random.uniform(0, 1), 2),
            "product_views_30d": random.randint(0, 100),
            # Customer Service
            "support_tickets_total": random.randint(0, 10),
            "support_tickets_open": random.randint(0, 3),
            "returns_count": random.randint(0, 5),
            "refunds_count": random.randint(0, 3),
            # Preferences
            "favorite_category": random.choice(
                ["Fashion", "Electronics", "Home", "Sports", "Books"]
            ),
            "discount_usage_rate": round(random.uniform(0, 1), 2),
            "premium_product_rate": round(random.uniform(0, 1), 2),
            # Payment & Shipping
            "payment_method": random.choice(
                ["Credit Card", "PayPal", "Debit Card", "Bank Transfer"]
            ),
            "shipping_method": random.choice(["Standard", "Express", "Next Day"]),
            "failed_payment_count": random.randint(0, 3),
        }

    @task(10)
    def predict_churn(self) -> None:
        """Test prediction endpoint (most common).

        Weight: 10 (10x more likely than other tasks)
        """
        customer_data = self.generate_customer_data()

        with self.client.post(
            "/predict",
            json=customer_data,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Verify response structure
                if all(k in data for k in ["request_id", "churn_probability", "risk_score"]):
                    response.success()
                else:
                    response.failure("Missing required fields in response")
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def health_check(self) -> None:
        """Test health endpoint.

        Weight: 1 (less frequent)
        """
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure("Service not healthy")
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(2)
    def router_metrics(self) -> None:
        """Test router metrics endpoint.

        Weight: 2 (monitoring)
        """
        with self.client.get(
            "/router/metrics", headers=self.headers, catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.status_code}")


class HighLoadUser(HttpUser):
    """User that generates high load (stress testing)."""

    wait_time = between(0.1, 0.5)  # Very fast requests

    def on_start(self) -> None:
        """Initialize user session."""
        self.api_key = "sk_test_your_api_key_here"
        self.headers = {"X-API-Key": self.api_key}

    @task
    def rapid_predictions(self) -> None:
        """Make rapid prediction requests."""
        customer_data = {
            "customer_age_days": 365,
            "account_age_days": 365,
            "total_orders": 10,
            "total_revenue": 500.0,
            "avg_order_value": 50.0,
            "days_since_last_order": 30,
            "order_frequency": 1.0,
            "website_visits_30d": 5,
            "email_open_rate": 0.5,
            "cart_abandonment_rate": 0.3,
            "product_views_30d": 10,
            "support_tickets_total": 1,
            "support_tickets_open": 0,
            "returns_count": 1,
            "refunds_count": 0,
            "favorite_category": "Fashion",
            "discount_usage_rate": 0.3,
            "premium_product_rate": 0.5,
            "payment_method": "Credit Card",
            "shipping_method": "Standard",
            "failed_payment_count": 0,
        }

        self.client.post("/predict", json=customer_data, headers=self.headers)


class BurstLoadUser(HttpUser):
    """User that simulates burst traffic patterns."""

    wait_time = between(5, 10)  # Long wait between bursts

    def on_start(self) -> None:
        """Initialize user session."""
        self.api_key = "sk_test_your_api_key_here"
        self.headers = {"X-API-Key": self.api_key}

    @task
    def burst_requests(self) -> None:
        """Make burst of requests."""
        # Simulate burst (e.g., batch processing)
        for _ in range(10):
            customer_data = {
                "customer_age_days": random.randint(30, 1000),
                "account_age_days": random.randint(30, 1000),
                "total_orders": random.randint(1, 50),
                "total_revenue": round(random.uniform(100, 2000), 2),
                "avg_order_value": round(random.uniform(30, 150), 2),
                "days_since_last_order": random.randint(0, 180),
                "order_frequency": round(random.uniform(0.5, 3.0), 2),
                "website_visits_30d": random.randint(5, 30),
                "email_open_rate": round(random.uniform(0.2, 0.8), 2),
                "cart_abandonment_rate": round(random.uniform(0.1, 0.6), 2),
                "product_views_30d": random.randint(10, 50),
                "support_tickets_total": random.randint(0, 5),
                "support_tickets_open": random.randint(0, 1),
                "returns_count": random.randint(0, 3),
                "refunds_count": random.randint(0, 2),
                "favorite_category": random.choice(["Fashion", "Electronics", "Home"]),
                "discount_usage_rate": round(random.uniform(0.2, 0.7), 2),
                "premium_product_rate": round(random.uniform(0.3, 0.8), 2),
                "payment_method": random.choice(["Credit Card", "PayPal"]),
                "shipping_method": random.choice(["Standard", "Express"]),
                "failed_payment_count": random.randint(0, 1),
            }

            self.client.post("/predict", json=customer_data, headers=self.headers)
            time.sleep(0.1)  # Small delay between burst requests
