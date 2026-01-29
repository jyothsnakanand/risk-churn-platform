"""
Synthetic Data Generator for E-Commerce Churn Platform

Generates realistic customer data with controlled drift and varying risk levels.
Feeds data into Kafka to demonstrate:
- Risk progression (low to high risk customers)
- Churn patterns
- Feature drift over time
"""

import random
from datetime import datetime, timedelta

import numpy as np


class SyntheticDataGenerator:
    """Generate synthetic customer data with realistic patterns and drift."""

    def __init__(self, seed: int | None = None):
        """Initialize the generator with optional seed for reproducibility."""
        if seed:
            random.seed(seed)
            np.random.seed(seed)

        self.categories = [
            "Electronics",
            "Fashion",
            "Home & Garden",
            "Sports",
            "Books",
            "Beauty",
            "Toys",
            "Food & Beverage",
        ]

        self.payment_methods = ["Credit Card", "Debit Card", "PayPal", "Bank Transfer"]
        self.shipping_methods = ["Standard", "Express", "Next Day", "Economy"]

        # Drift parameters (will change over time)
        self.drift_factor = 0.0  # 0 to 1, controls how much drift to apply
        self.drift_direction = 1  # 1 for increasing, -1 for decreasing

    def set_drift(self, factor: float, direction: int = 1):
        """
        Set the drift factor and direction.

        Args:
            factor: Drift amount (0 to 1)
            direction: 1 for increasing drift, -1 for decreasing
        """
        self.drift_factor = max(0.0, min(1.0, factor))
        self.drift_direction = direction

    def generate_customer(self, risk_level: str = "random") -> dict:
        """
        Generate a single customer with specified risk level.

        Args:
            risk_level: "low", "medium", "high", or "random"

        Returns:
            Dictionary with customer features
        """
        if risk_level == "random":
            risk_level = random.choice(["low", "medium", "high"])

        if risk_level == "low":
            return self._generate_low_risk_customer()
        elif risk_level == "medium":
            return self._generate_medium_risk_customer()
        else:
            return self._generate_high_risk_customer()

    def _generate_low_risk_customer(self) -> dict:
        """Generate a loyal, engaged customer with low churn risk."""
        # Apply drift to make customers gradually worse over time
        drift_multiplier = 1.0 - (self.drift_factor * 0.3 * self.drift_direction)

        customer_age_days = int(random.uniform(365, 1825) * drift_multiplier)  # 1-5 years
        account_age_days = int(random.uniform(180, customer_age_days))

        total_orders = int(random.uniform(20, 100) * drift_multiplier)
        total_revenue = random.uniform(2000, 15000) * drift_multiplier
        avg_order_value = total_revenue / total_orders

        # Low risk indicators
        days_since_last_order = int(random.uniform(1, 14) * (1 + self.drift_factor * 0.5))
        order_frequency = random.uniform(1.5, 4.0) * drift_multiplier

        # High engagement
        website_visits_30d = int(random.uniform(15, 40) * drift_multiplier)
        email_open_rate = random.uniform(0.60, 0.95) * drift_multiplier
        cart_abandonment_rate = random.uniform(0.05, 0.25) * (1 + self.drift_factor * 0.3)
        product_views_30d = int(random.uniform(30, 100) * drift_multiplier)

        # Good customer service history
        support_tickets_total = random.randint(0, 3)
        support_tickets_open = 0
        returns_count = random.randint(0, 2)
        refunds_count = random.randint(0, 1)

        # Add randomness
        favorite_category = random.choice(self.categories)
        discount_usage_rate = random.uniform(0.10, 0.40)
        premium_product_rate = random.uniform(0.30, 0.70) * drift_multiplier

        payment_method = random.choice(self.payment_methods)
        shipping_method = random.choice(self.shipping_methods)
        failed_payment_count = 0 if random.random() > 0.1 else 1

        return {
            "customer_age_days": customer_age_days,
            "account_age_days": account_age_days,
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "avg_order_value": round(avg_order_value, 2),
            "days_since_last_order": days_since_last_order,
            "order_frequency": round(order_frequency, 2),
            "website_visits_30d": website_visits_30d,
            "email_open_rate": round(email_open_rate, 2),
            "cart_abandonment_rate": round(cart_abandonment_rate, 2),
            "product_views_30d": product_views_30d,
            "support_tickets_total": support_tickets_total,
            "support_tickets_open": support_tickets_open,
            "returns_count": returns_count,
            "refunds_count": refunds_count,
            "favorite_category": favorite_category,
            "discount_usage_rate": round(discount_usage_rate, 2),
            "premium_product_rate": round(premium_product_rate, 2),
            "payment_method": payment_method,
            "shipping_method": shipping_method,
            "failed_payment_count": failed_payment_count,
            "true_risk_level": "low",
        }

    def _generate_medium_risk_customer(self) -> dict:
        """Generate a customer showing some warning signs."""
        # Apply drift - medium risk customers can shift either way
        drift_multiplier = 1.0 + (
            self.drift_factor * 0.2 * self.drift_direction * random.choice([-1, 1])
        )

        customer_age_days = int(random.uniform(180, 730))  # 6 months - 2 years
        account_age_days = int(random.uniform(90, customer_age_days))

        total_orders = int(random.uniform(5, 20))
        total_revenue = random.uniform(300, 2000)
        avg_order_value = total_revenue / total_orders

        # Medium risk indicators
        days_since_last_order = int(random.uniform(15, 45) * (1 + self.drift_factor * 0.5))
        order_frequency = random.uniform(0.3, 1.5) * drift_multiplier

        # Moderate engagement
        website_visits_30d = int(random.uniform(5, 15))
        email_open_rate = random.uniform(0.30, 0.60) * drift_multiplier
        cart_abandonment_rate = random.uniform(0.35, 0.65) * (1 + self.drift_factor * 0.3)
        product_views_30d = int(random.uniform(10, 30))

        # Some issues
        support_tickets_total = random.randint(2, 5)
        support_tickets_open = random.randint(0, 1)
        returns_count = random.randint(1, 4)
        refunds_count = random.randint(0, 2)

        # Add randomness
        favorite_category = random.choice(self.categories)
        discount_usage_rate = random.uniform(0.40, 0.70)
        premium_product_rate = random.uniform(0.10, 0.40)

        payment_method = random.choice(self.payment_methods)
        shipping_method = random.choice(self.shipping_methods)
        failed_payment_count = random.randint(0, 2)

        return {
            "customer_age_days": customer_age_days,
            "account_age_days": account_age_days,
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "avg_order_value": round(avg_order_value, 2),
            "days_since_last_order": days_since_last_order,
            "order_frequency": round(order_frequency, 2),
            "website_visits_30d": website_visits_30d,
            "email_open_rate": round(email_open_rate, 2),
            "cart_abandonment_rate": round(cart_abandonment_rate, 2),
            "product_views_30d": product_views_30d,
            "support_tickets_total": support_tickets_total,
            "support_tickets_open": support_tickets_open,
            "returns_count": returns_count,
            "refunds_count": refunds_count,
            "favorite_category": favorite_category,
            "discount_usage_rate": round(discount_usage_rate, 2),
            "premium_product_rate": round(premium_product_rate, 2),
            "payment_method": payment_method,
            "shipping_method": shipping_method,
            "failed_payment_count": failed_payment_count,
            "true_risk_level": "medium",
        }

    def _generate_high_risk_customer(self) -> dict:
        """Generate a customer at high risk of churning."""
        # Apply drift to make high-risk customers even worse
        drift_multiplier = 1.0 + (self.drift_factor * 0.4 * self.drift_direction)

        customer_age_days = int(random.uniform(90, 365))  # 3-12 months
        account_age_days = int(random.uniform(30, customer_age_days))

        total_orders = int(random.uniform(1, 8))
        total_revenue = random.uniform(50, 500)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 50.0

        # High risk indicators
        days_since_last_order = int(random.uniform(45, 120) * drift_multiplier)
        order_frequency = random.uniform(0.05, 0.3) / drift_multiplier

        # Low engagement
        website_visits_30d = int(random.uniform(0, 5) / drift_multiplier)
        email_open_rate = random.uniform(0.0, 0.30) / drift_multiplier
        cart_abandonment_rate = random.uniform(0.70, 0.95) * drift_multiplier
        product_views_30d = int(random.uniform(0, 10) / drift_multiplier)

        # Customer service issues
        support_tickets_total = random.randint(3, 10)
        support_tickets_open = random.randint(1, 3)
        returns_count = random.randint(2, 6)
        refunds_count = random.randint(1, 4)

        # Add randomness
        favorite_category = random.choice(self.categories)
        discount_usage_rate = random.uniform(0.70, 0.95)  # Only buys on discount
        premium_product_rate = random.uniform(0.0, 0.15)  # Rarely buys premium

        payment_method = random.choice(self.payment_methods)
        shipping_method = random.choice(self.shipping_methods)
        failed_payment_count = random.randint(1, 5)

        return {
            "customer_age_days": customer_age_days,
            "account_age_days": account_age_days,
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "avg_order_value": round(avg_order_value, 2),
            "days_since_last_order": days_since_last_order,
            "order_frequency": round(order_frequency, 2),
            "website_visits_30d": website_visits_30d,
            "email_open_rate": round(email_open_rate, 2),
            "cart_abandonment_rate": round(cart_abandonment_rate, 2),
            "product_views_30d": product_views_30d,
            "support_tickets_total": support_tickets_total,
            "support_tickets_open": support_tickets_open,
            "returns_count": returns_count,
            "refunds_count": refunds_count,
            "favorite_category": favorite_category,
            "discount_usage_rate": round(discount_usage_rate, 2),
            "premium_product_rate": round(premium_product_rate, 2),
            "payment_method": payment_method,
            "shipping_method": shipping_method,
            "failed_payment_count": failed_payment_count,
            "true_risk_level": "high",
        }

    def generate_batch(
        self, count: int, risk_distribution: dict[str, float] | None = None
    ) -> list[dict]:
        """
        Generate a batch of customers.

        Args:
            count: Number of customers to generate
            risk_distribution: Dict with 'low', 'medium', 'high' percentages (should sum to 1.0)
                              Default: {'low': 0.5, 'medium': 0.3, 'high': 0.2}

        Returns:
            List of customer dictionaries
        """
        if risk_distribution is None:
            risk_distribution = {"low": 0.5, "medium": 0.3, "high": 0.2}

        customers = []
        for _ in range(count):
            rand = random.random()
            if rand < risk_distribution["low"]:
                risk_level = "low"
            elif rand < risk_distribution["low"] + risk_distribution["medium"]:
                risk_level = "medium"
            else:
                risk_level = "high"

            customers.append(self.generate_customer(risk_level))

        return customers

    def simulate_customer_lifecycle(self, customer_id: str, duration_days: int = 180) -> list[dict]:
        """
        Simulate a customer's lifecycle showing progression from low to high risk.

        Args:
            customer_id: Unique identifier for the customer
            duration_days: Number of days to simulate

        Returns:
            List of customer snapshots over time
        """
        snapshots = []

        # Start with a good customer
        base_customer = self._generate_low_risk_customer()
        base_customer["customer_id"] = customer_id

        # Generate snapshots showing gradual degradation
        for day in range(0, duration_days, 7):  # Weekly snapshots
            progress = day / duration_days  # 0 to 1

            # Create degraded version
            snapshot = base_customer.copy()
            snapshot["snapshot_date"] = (
                datetime.now() - timedelta(days=duration_days - day)
            ).isoformat()

            # Degrade metrics over time
            snapshot["days_since_last_order"] = int(
                base_customer["days_since_last_order"] * (1 + progress * 5)
            )
            snapshot["order_frequency"] = round(
                base_customer["order_frequency"] * (1 - progress * 0.7), 2
            )
            snapshot["website_visits_30d"] = int(
                base_customer["website_visits_30d"] * (1 - progress * 0.8)
            )
            snapshot["email_open_rate"] = round(
                base_customer["email_open_rate"] * (1 - progress * 0.6), 2
            )
            snapshot["cart_abandonment_rate"] = round(
                min(0.95, base_customer["cart_abandonment_rate"] * (1 + progress * 2)), 2
            )
            snapshot["support_tickets_open"] = int(progress * 3)

            # Update risk level
            if progress < 0.3:
                snapshot["true_risk_level"] = "low"
            elif progress < 0.7:
                snapshot["true_risk_level"] = "medium"
            else:
                snapshot["true_risk_level"] = "high"

            snapshots.append(snapshot)

        return snapshots
