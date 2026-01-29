#!/usr/bin/env python3
"""
Example: Using the Synthetic Data Generator

This script demonstrates various ways to generate customer data
for testing and demonstration purposes.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from risk_churn_platform.data_generator import SyntheticDataGenerator


def example_1_basic_generation():
    """Example 1: Generate customers with different risk levels."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Customer Generation")
    print("=" * 70)

    generator = SyntheticDataGenerator(seed=42)

    # Generate different risk levels
    print("\n[Low Risk Customer]")
    low_risk = generator.generate_customer("low")
    print(f"  Order Frequency: {low_risk['order_frequency']:.2f}/month")
    print(f"  Days Since Last Order: {low_risk['days_since_last_order']}")
    print(f"  Email Open Rate: {low_risk['email_open_rate']:.1%}")
    print(f"  Cart Abandonment: {low_risk['cart_abandonment_rate']:.1%}")
    print(f"  Risk Level: {low_risk['true_risk_level']}")

    print("\n[Medium Risk Customer]")
    medium_risk = generator.generate_customer("medium")
    print(f"  Order Frequency: {medium_risk['order_frequency']:.2f}/month")
    print(f"  Days Since Last Order: {medium_risk['days_since_last_order']}")
    print(f"  Email Open Rate: {medium_risk['email_open_rate']:.1%}")
    print(f"  Cart Abandonment: {medium_risk['cart_abandonment_rate']:.1%}")
    print(f"  Risk Level: {medium_risk['true_risk_level']}")

    print("\n[High Risk Customer]")
    high_risk = generator.generate_customer("high")
    print(f"  Order Frequency: {high_risk['order_frequency']:.2f}/month")
    print(f"  Days Since Last Order: {high_risk['days_since_last_order']}")
    print(f"  Email Open Rate: {high_risk['email_open_rate']:.1%}")
    print(f"  Cart Abandonment: {high_risk['cart_abandonment_rate']:.1%}")
    print(f"  Risk Level: {high_risk['true_risk_level']}")


def example_2_batch_generation():
    """Example 2: Generate a batch of customers."""
    print("\n" + "=" * 70)
    print("Example 2: Batch Generation")
    print("=" * 70)

    generator = SyntheticDataGenerator()

    # Generate 100 customers with custom distribution
    customers = generator.generate_batch(
        count=100, risk_distribution={"low": 0.5, "medium": 0.3, "high": 0.2}
    )

    # Analyze the batch
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    total_revenue = 0

    for customer in customers:
        risk_counts[customer["true_risk_level"]] += 1
        total_revenue += customer["total_revenue"]

    print(f"\nGenerated {len(customers)} customers:")
    print(f"  Low Risk: {risk_counts['low']} ({risk_counts['low']/len(customers):.1%})")
    print(f"  Medium Risk: {risk_counts['medium']} ({risk_counts['medium']/len(customers):.1%})")
    print(f"  High Risk: {risk_counts['high']} ({risk_counts['high']/len(customers):.1%})")
    print(f"\nTotal Revenue: ${total_revenue:,.2f}")
    print(f"Average Revenue per Customer: ${total_revenue/len(customers):,.2f}")


def example_3_drift_simulation():
    """Example 3: Demonstrate feature drift."""
    print("\n" + "=" * 70)
    print("Example 3: Feature Drift Simulation")
    print("=" * 70)

    generator = SyntheticDataGenerator(seed=42)

    # Generate customer with no drift
    print("\n[No Drift]")
    customer_no_drift = generator.generate_customer("low")
    print(f"  Order Frequency: {customer_no_drift['order_frequency']:.2f}")
    print(f"  Email Open Rate: {customer_no_drift['email_open_rate']:.1%}")
    print(f"  Website Visits: {customer_no_drift['website_visits_30d']}")

    # Apply 50% drift
    generator.set_drift(factor=0.5, direction=1)
    print("\n[50% Drift Applied]")
    customer_drift_50 = generator.generate_customer("low")
    print(f"  Order Frequency: {customer_drift_50['order_frequency']:.2f}")
    print(f"  Email Open Rate: {customer_drift_50['email_open_rate']:.1%}")
    print(f"  Website Visits: {customer_drift_50['website_visits_30d']}")

    # Apply 100% drift
    generator.set_drift(factor=1.0, direction=1)
    print("\n[100% Drift Applied]")
    customer_drift_100 = generator.generate_customer("low")
    print(f"  Order Frequency: {customer_drift_100['order_frequency']:.2f}")
    print(f"  Email Open Rate: {customer_drift_100['email_open_rate']:.1%}")
    print(f"  Website Visits: {customer_drift_100['website_visits_30d']}")

    print("\nNote: Even 'low risk' customers show degraded metrics with drift")


def example_4_lifecycle_simulation():
    """Example 4: Simulate customer lifecycle."""
    print("\n" + "=" * 70)
    print("Example 4: Customer Lifecycle Simulation")
    print("=" * 70)

    generator = SyntheticDataGenerator(seed=42)

    # Simulate 180-day lifecycle
    snapshots = generator.simulate_customer_lifecycle(
        customer_id="example_customer", duration_days=180
    )

    print(f"\nGenerated {len(snapshots)} snapshots over 180 days (weekly):\n")
    print(f"{'Week':<6} {'Days Since':<12} {'Order Freq':<12} {'Email Open':<12} {'Risk Level'}")
    print("-" * 60)

    for i, snapshot in enumerate(snapshots[::2]):  # Show every other week
        week = i * 2 + 1
        print(
            f"{week:<6} "
            f"{snapshot['days_since_last_order']:<12} "
            f"{snapshot['order_frequency']:<12.2f} "
            f"{snapshot['email_open_rate']:<12.1%} "
            f"{snapshot['true_risk_level']}"
        )

    print("\nObserve how the customer degrades from low → medium → high risk")


def example_5_save_to_file():
    """Example 5: Generate and save data to file."""
    print("\n" + "=" * 70)
    print("Example 5: Save Generated Data")
    print("=" * 70)

    generator = SyntheticDataGenerator(seed=42)

    # Generate training dataset
    customers = generator.generate_batch(count=50)

    # Save to JSON
    output_file = "sample_customers.json"
    with open(output_file, "w") as f:
        json.dump(customers, f, indent=2)

    print(f"\nGenerated {len(customers)} customers")
    print(f"Saved to: {output_file}")
    print(f"File size: {Path(output_file).stat().st_size:,} bytes")

    # Sample
    print("\nSample customer (first record):")
    sample = customers[0]
    print(f"  Customer Age: {sample['customer_age_days']/365:.1f} years")
    print(f"  Total Orders: {sample['total_orders']}")
    print(f"  Total Revenue: ${sample['total_revenue']:.2f}")
    print(f"  Risk Level: {sample['true_risk_level']}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("SYNTHETIC DATA GENERATOR EXAMPLES")
    print("=" * 70)

    try:
        example_1_basic_generation()
        example_2_batch_generation()
        example_3_drift_simulation()
        example_4_lifecycle_simulation()
        example_5_save_to_file()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETE")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Review the generated 'sample_customers.json' file")
        print("  2. Try streaming data: python scripts/generate_synthetic_data.py stream")
        print("  3. Read the full documentation: docs/DATA_GENERATOR.md")
        print()

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
