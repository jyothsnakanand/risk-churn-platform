#!/usr/bin/env python3
"""
Examples: Using Real E-Commerce Dataset

Demonstrates how to work with the real e-commerce dataset for
training, testing, and streaming.
"""

import sys
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from risk_churn_platform.data_generator import EcommerceDataLoader, get_sample_customer


def example_1_load_and_process():
    """Example 1: Load and process real events."""
    print("\n" + "=" * 70)
    print("Example 1: Load and Process Real Events")
    print("=" * 70)

    loader = EcommerceDataLoader("data/ecommerce")

    # Load sample of events
    print("\nLoading 5,000 events...")
    events = loader.load_events(sample_size=5000)

    print(f"Loaded {len(events):,} events")
    print("\nEvent types:")
    print(events["event"].value_counts())

    print(f"\nUnique visitors: {events['visitorid'].nunique():,}")
    print(f"\nDate range: {events['timestamp'].min()} to {events['timestamp'].max()}")

    # Aggregate to customer level
    print("\nAggregating customer features...")
    customers = loader.aggregate_customer_features(events)

    print(f"\nCreated features for {len(customers):,} customers")
    print("\nRisk distribution:")
    print(customers["true_risk_level"].value_counts())

    return customers


def example_2_explore_customers():
    """Example 2: Explore processed customer data."""
    print("\n" + "=" * 70)
    print("Example 2: Explore Processed Customers")
    print("=" * 70)

    # Check if processed data exists
    processed_file = "data/ecommerce/test_processed.csv"
    if not Path(processed_file).exists():
        print(f"\n⚠ Processed file not found: {processed_file}")
        print("Run preprocessing first:")
        print("  python scripts/preprocess_real_data.py --sample 10000")
        return

    # Load processed data
    df = pd.read_csv(processed_file)

    print(f"\nLoaded {len(df):,} processed customers")

    # Show statistics
    print("\nOrder Statistics:")
    print(f"  Avg orders: {df['total_orders'].mean():.2f}")
    print(f"  Max orders: {df['total_orders'].max()}")
    print(f"  Customers with orders: {len(df[df['total_orders'] > 0]):,}")

    print("\nEngagement Metrics:")
    print(f"  Avg product views: {df['product_views_30d'].mean():.1f}")
    print(f"  Avg cart abandonment: {df['cart_abandonment_rate'].mean():.1%}")

    # Find interesting customers
    print("\nCustomer Segments:")

    # High-value customers (3+ orders)
    high_value = df[df["total_orders"] >= 3]
    print(f"  High-value (3+ orders): {len(high_value):,}")

    # Active browsers (no orders but high engagement)
    active_browsers = df[(df["total_orders"] == 0) & (df["product_views_30d"] > 10)]
    print(f"  Active browsers (0 orders, 10+ views): {len(active_browsers):,}")

    # Cart abandoners
    cart_abandoners = df[df["cart_abandonment_rate"] > 0.5]
    print(f"  Cart abandoners (>50% rate): {len(cart_abandoners):,}")

    # Sample customers
    print("\nSample Customers:")
    samples = df.sample(min(3, len(df)))
    for _, customer in samples.iterrows():
        print(
            f"\n  {customer['customer_id']}: "
            f"{customer['total_orders']} orders, "
            f"{customer['product_views_30d']} views, "
            f"risk={customer['true_risk_level']}"
        )


def example_3_get_sample_customer():
    """Example 3: Get a sample customer."""
    print("\n" + "=" * 70)
    print("Example 3: Get Sample Customer")
    print("=" * 70)

    try:
        customer = get_sample_customer()

        print(f"\nRandom customer: {customer['customer_id']}")
        print(f"  Customer age: {customer['customer_age_days']} days")
        print(f"  Total orders: {customer['total_orders']}")
        print(f"  Total revenue: ${customer['total_revenue']:.2f}")
        print(f"  Days since last order: {customer['days_since_last_order']}")
        print(f"  Product views (30d): {customer['product_views_30d']}")
        print(f"  Cart abandonment: {customer['cart_abandonment_rate']:.1%}")
        print(f"  Risk level: {customer['true_risk_level']}")
        print(f"  Data source: {customer['data_source']}")

    except FileNotFoundError as e:
        print(f"\n⚠ {e}")
        print("\nRun preprocessing first:")
        print("  python scripts/preprocess_real_data.py")


def example_4_compare_synthetic_vs_real():
    """Example 4: Compare synthetic vs real data distributions."""
    print("\n" + "=" * 70)
    print("Example 4: Compare Synthetic vs Real Data")
    print("=" * 70)

    from risk_churn_platform.data_generator import SyntheticDataGenerator

    # Generate synthetic data
    print("\nGenerating 1,000 synthetic customers...")
    synthetic_gen = SyntheticDataGenerator(seed=42)
    synthetic = pd.DataFrame(synthetic_gen.generate_batch(1000))

    # Load real data
    processed_file = "data/ecommerce/test_processed.csv"
    if not Path(processed_file).exists():
        print("\n⚠ Real data not found. Run preprocessing first.")
        return

    real = pd.read_csv(processed_file)

    # Compare distributions
    print("\nRisk Distribution Comparison:")
    print("\nSynthetic:")
    print(synthetic["true_risk_level"].value_counts(normalize=True).apply(lambda x: f"{x:.1%}"))

    print("\nReal:")
    print(real["true_risk_level"].value_counts(normalize=True).apply(lambda x: f"{x:.1%}"))

    print("\nOrder Frequency Comparison:")
    print(f"  Synthetic avg: {synthetic['order_frequency'].mean():.2f}")
    print(f"  Real avg: {real['order_frequency'].mean():.2f}")

    print("\nProduct Views Comparison:")
    print(f"  Synthetic avg: {synthetic['product_views_30d'].mean():.1f}")
    print(f"  Real avg: {real['product_views_30d'].mean():.1f}")

    print("\nKey Insights:")
    print("  - Real data has more high-risk customers (browsers who never purchase)")
    print("  - Synthetic data is more balanced for training")
    print("  - Consider mixing both for robust models")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("REAL E-COMMERCE DATA EXAMPLES")
    print("=" * 70)

    try:
        # Example 1: Load and process
        example_1_load_and_process()

        # Example 2: Explore processed data
        example_2_explore_customers()

        # Example 3: Get sample customer
        example_3_get_sample_customer()

        # Example 4: Compare synthetic vs real
        example_4_compare_synthetic_vs_real()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETE")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Process the full dataset:")
        print("     python scripts/preprocess_real_data.py --sample 100000")
        print("  2. Train models on real data")
        print("  3. Combine with synthetic data for balanced training")
        print()

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
