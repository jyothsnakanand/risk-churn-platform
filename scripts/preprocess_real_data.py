#!/usr/bin/env python3
"""
Preprocess Real E-Commerce Dataset

Processes the raw e-commerce dataset and creates customer-level features
ready for training and prediction.

Usage:
    python scripts/preprocess_real_data.py --sample 100000 --output data/ecommerce/processed_customers.csv
    python scripts/preprocess_real_data.py --full  # Process entire dataset (takes longer)
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from risk_churn_platform.data_generator.real_data_loader import EcommerceDataLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Preprocess real e-commerce dataset")
    parser.add_argument(
        "--sample",
        type=int,
        default=100000,
        help="Number of events to sample (default: 100000). Use --full to process all data.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Process the entire dataset (WARNING: may take several minutes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/ecommerce/processed_customers.csv",
        help="Output CSV file path",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/ecommerce",
        help="Directory containing raw dataset files",
    )

    args = parser.parse_args()

    # Check if data directory exists
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        logger.error("Please extract the dataset first:")
        logger.error("  unzip ecommerce-dataset.zip -d data/ecommerce")
        sys.exit(1)

    # Check required files
    required_files = ["events.csv", "category_tree.csv"]
    missing_files = [f for f in required_files if not (data_dir / f).exists()]
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        sys.exit(1)

    # Initialize loader
    loader = EcommerceDataLoader(data_dir=str(data_dir))

    # Determine sample size
    sample_size = None if args.full else args.sample

    if args.full:
        logger.warning(
            "Processing FULL dataset - this may take 10-15 minutes and use significant memory"
        )
        response = input("Continue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            logger.info("Cancelled")
            sys.exit(0)

    # Create dataset
    logger.info("=" * 70)
    logger.info("E-COMMERCE DATASET PREPROCESSING")
    logger.info("=" * 70)

    try:
        customers_df = loader.create_training_dataset(
            output_path=args.output, sample_size=sample_size
        )

        logger.info("\n" + "=" * 70)
        logger.info("PREPROCESSING COMPLETE")
        logger.info("=" * 70)
        logger.info(f"\nProcessed customer data saved to: {args.output}")
        logger.info(f"Total customers: {len(customers_df):,}")
        logger.info("\nYou can now:")
        logger.info("  1. Use this data for model training")
        logger.info("  2. Stream real customers to Kafka:")
        logger.info("     python scripts/stream_real_data.py --rate 30 --duration 5")
        logger.info("  3. Train models on real data:")
        logger.info("     python scripts/train_on_real_data.py")

    except Exception as e:
        logger.error(f"Error during preprocessing: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
