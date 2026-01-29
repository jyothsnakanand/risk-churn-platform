"""
Real E-Commerce Dataset Loader

Loads and processes the real e-commerce dataset to extract customer features
compatible with the churn prediction platform.

Dataset: E-commerce behavior data from cosmetics shop
Source: https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset
"""

import logging
from datetime import timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class EcommerceDataLoader:
    """Load and process real e-commerce dataset."""

    def __init__(self, data_dir: str = "data/ecommerce"):
        """
        Initialize the data loader.

        Args:
            data_dir: Directory containing the dataset files
        """
        self.data_dir = Path(data_dir)
        self.events_df: pd.DataFrame | None = None
        self.categories_df: pd.DataFrame | None = None
        self.items_df: pd.DataFrame | None = None

    def load_events(self, sample_size: int | None = None) -> pd.DataFrame:
        """
        Load events data (user interactions).

        Args:
            sample_size: If specified, sample only this many rows

        Returns:
            DataFrame with events
        """
        logger.info("Loading events data...")
        events_path = self.data_dir / "events.csv"

        events_df: pd.DataFrame
        if sample_size:
            # Read in chunks and sample
            chunk_size = 100000
            chunks = []
            rows_read = 0

            for chunk in pd.read_csv(events_path, chunksize=chunk_size):
                chunks.append(chunk)
                rows_read += len(chunk)
                if rows_read >= sample_size:
                    break

            events_df = pd.concat(chunks, ignore_index=True).head(sample_size)
        else:
            events_df = pd.read_csv(events_path)

        # Convert timestamp to datetime
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], unit="ms")
        self.events_df = events_df

        logger.info(f"Loaded {len(events_df):,} events")
        return events_df

    def load_categories(self) -> pd.DataFrame:
        """Load category tree."""
        logger.info("Loading category tree...")
        categories_df = pd.read_csv(self.data_dir / "category_tree.csv")
        self.categories_df = categories_df
        logger.info(f"Loaded {len(categories_df):,} categories")
        return categories_df

    def aggregate_customer_features(
        self, events_df: pd.DataFrame | None = None, window_days: int = 180
    ) -> pd.DataFrame:
        """
        Aggregate customer-level features from events.

        Args:
            events_df: Events DataFrame (uses loaded data if None)
            window_days: Number of days to look back

        Returns:
            DataFrame with customer features
        """
        if events_df is None:
            if self.events_df is None:
                raise ValueError("No events data loaded. Call load_events() first.")
            events_df = self.events_df

        logger.info("Aggregating customer features...")

        # Get cutoff date (most recent date in dataset)
        max_date = events_df["timestamp"].max()
        cutoff_date = max_date - timedelta(days=window_days)

        # Filter to window
        events_window = events_df[events_df["timestamp"] >= cutoff_date].copy()

        # Aggregate by customer (visitorid)
        customer_features = []

        for visitor_id, visitor_events in events_window.groupby("visitorid"):
            # Sort by timestamp
            visitor_events = visitor_events.sort_values("timestamp")

            # Basic temporal features
            first_event = visitor_events["timestamp"].min()
            last_event = visitor_events["timestamp"].max()
            customer_age_days = (max_date - first_event).days
            days_since_last_event = (max_date - last_event).days

            # Event counts
            total_events = len(visitor_events)
            view_count = len(visitor_events[visitor_events["event"] == "view"])
            addtocart_count = len(visitor_events[visitor_events["event"] == "addtocart"])
            transaction_count = len(visitor_events[visitor_events["event"] == "transaction"])

            # Engagement metrics
            cart_abandonment_rate = (
                (addtocart_count - transaction_count) / max(1, addtocart_count)
                if addtocart_count > 0
                else 0.0
            )

            # Purchase behavior
            transactions = visitor_events[visitor_events["event"] == "transaction"]
            total_orders = len(transactions["transactionid"].unique())

            # Unique items viewed
            unique_items_viewed = visitor_events["itemid"].nunique()

            # Session estimation (gap > 30 min = new session)
            visitor_events["time_diff"] = visitor_events["timestamp"].diff()
            sessions = (visitor_events["time_diff"] > timedelta(minutes=30)).sum() + 1

            # Build feature dict
            features = {
                "customer_id": f"visitor_{visitor_id}",
                "customer_age_days": customer_age_days,
                "account_age_days": customer_age_days,  # Same as customer age
                "total_orders": total_orders,
                "total_revenue": total_orders * 100.0,  # Estimate $100 per order (no price data)
                "avg_order_value": 100.0 if total_orders > 0 else 0.0,
                "days_since_last_order": days_since_last_event if total_orders > 0 else 999,
                "order_frequency": total_orders / max(1, customer_age_days / 30),
                "website_visits_30d": sessions,
                "email_open_rate": 0.5,  # Not available - use default
                "cart_abandonment_rate": min(1.0, max(0.0, cart_abandonment_rate)),
                "product_views_30d": view_count,
                "support_tickets_total": 0,  # Not available
                "support_tickets_open": 0,  # Not available
                "returns_count": 0,  # Not available
                "refunds_count": 0,  # Not available
                "favorite_category": "Unknown",  # Would need item properties
                "discount_usage_rate": 0.3,  # Not available - use default
                "premium_product_rate": 0.2,  # Not available - use default
                "payment_method": "Credit Card",  # Not available
                "shipping_method": "Standard",  # Not available
                "failed_payment_count": 0,  # Not available
                # Real data indicators
                "data_source": "real",
                "total_events": total_events,
                "view_count": view_count,
                "addtocart_count": addtocart_count,
                "transaction_count": transaction_count,
                "unique_items_viewed": unique_items_viewed,
            }

            customer_features.append(features)

        df = pd.DataFrame(customer_features)

        # Assign risk levels based on actual behavior
        df["true_risk_level"] = df.apply(self._assign_risk_level, axis=1)

        logger.info(f"Aggregated features for {len(df):,} customers")
        return df

    def _assign_risk_level(self, row: pd.Series) -> str:
        """Assign risk level based on customer behavior."""
        # Low risk: Recent activity, multiple orders
        if row["days_since_last_order"] < 30 and row["total_orders"] >= 3:
            return "low"

        # High risk: No orders or very old activity
        if row["total_orders"] == 0 or row["days_since_last_order"] > 90:
            return "high"

        # Medium risk: everything else
        return "medium"

    def create_training_dataset(self, output_path: str, sample_size: int = 100000) -> pd.DataFrame:
        """
        Create a training dataset from the real data.

        Args:
            output_path: Where to save the CSV
            sample_size: Number of events to sample

        Returns:
            DataFrame with customer features
        """
        logger.info(f"Creating training dataset (sample size: {sample_size:,})...")

        # Load data
        events = self.load_events(sample_size=sample_size)

        # Aggregate features
        customers = self.aggregate_customer_features(events)

        # Save
        customers.to_csv(output_path, index=False)
        logger.info(f"Saved training dataset to {output_path}")

        # Print statistics
        self._print_dataset_stats(customers)

        return customers

    def _print_dataset_stats(self, df: pd.DataFrame) -> None:
        """Print dataset statistics."""
        logger.info("\nDataset Statistics:")
        logger.info(f"  Total customers: {len(df):,}")
        logger.info(
            f"  Risk distribution: "
            f"Low={len(df[df['true_risk_level']=='low']):,} ({len(df[df['true_risk_level']=='low'])/len(df)*100:.1f}%), "
            f"Medium={len(df[df['true_risk_level']=='medium']):,} ({len(df[df['true_risk_level']=='medium'])/len(df)*100:.1f}%), "
            f"High={len(df[df['true_risk_level']=='high']):,} ({len(df[df['true_risk_level']=='high'])/len(df)*100:.1f}%)"
        )
        logger.info(f"  Avg orders per customer: {df['total_orders'].mean():.2f}")
        logger.info(f"  Avg days since last order: {df['days_since_last_order'].mean():.1f}")
        logger.info(f"  Customers with 0 orders: {len(df[df['total_orders']==0]):,}")
        logger.info(f"  Customers with 3+ orders: {len(df[df['total_orders']>=3]):,}")


def get_sample_customer(customer_id: str | None = None) -> dict:
    """
    Get a sample customer from the real dataset.

    Args:
        customer_id: Specific customer ID to load, or random if None

    Returns:
        Customer feature dictionary
    """
    # Check if processed data exists
    processed_path = Path("data/ecommerce/processed_customers.csv")

    if processed_path.exists():
        df: pd.DataFrame = pd.read_csv(processed_path)
        if customer_id:
            customer = df[df["customer_id"] == customer_id]
            if len(customer) == 0:
                raise ValueError(f"Customer {customer_id} not found")
            return dict(customer.iloc[0].to_dict())
        else:
            # Return random customer
            return dict(df.sample(1).iloc[0].to_dict())
    else:
        raise FileNotFoundError(
            "Processed customer data not found. "
            "Run preprocessing script first: "
            "python scripts/preprocess_real_data.py"
        )
