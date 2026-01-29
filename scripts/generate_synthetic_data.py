#!/usr/bin/env python3
"""
CLI tool to generate and stream synthetic customer data to Kafka.

Usage examples:
  # Stream 60 customers/min for 10 minutes
  python scripts/generate_synthetic_data.py stream --rate 60 --duration 10

  # Generate drift scenario
  python scripts/generate_synthetic_data.py drift --duration 30

  # Simulate customer lifecycles
  python scripts/generate_synthetic_data.py lifecycle --customers 10

  # Generate a single batch and save to JSON
  python scripts/generate_synthetic_data.py batch --count 100 --output data.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from risk_churn_platform.data_generator import KafkaProducerService, SyntheticDataGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def stream_command(args):
    """Stream customers continuously to Kafka."""
    service = KafkaProducerService(bootstrap_servers=args.kafka_servers, topic=args.topic)

    risk_dist = None
    if args.low or args.medium or args.high:
        total = args.low + args.medium + args.high
        risk_dist = {
            "low": args.low / total,
            "medium": args.medium / total,
            "high": args.high / total,
        }
        logger.info(f"Using custom risk distribution: {risk_dist}")

    service.stream_customers(
        rate_per_minute=args.rate,
        duration_minutes=args.duration,
        risk_distribution=risk_dist,
        drift_progression=args.drift,
    )


def drift_command(args):
    """Generate data showing gradual drift."""
    service = KafkaProducerService(bootstrap_servers=args.kafka_servers, topic=args.topic)
    service.generate_drift_scenario(duration_minutes=args.duration)


def lifecycle_command(args):
    """Simulate customer lifecycles."""
    service = KafkaProducerService(bootstrap_servers=args.kafka_servers, topic=args.topic)
    service.simulate_lifecycle_stream(
        num_customers=args.customers, days_per_customer=args.days, speed_factor=args.speed
    )


def batch_command(args):
    """Generate a batch of customers."""
    generator = SyntheticDataGenerator(seed=args.seed)

    risk_dist = None
    if args.low or args.medium or args.high:
        total = args.low + args.medium + args.high
        risk_dist = {
            "low": args.low / total,
            "medium": args.medium / total,
            "high": args.high / total,
        }

    customers = generator.generate_batch(args.count, risk_distribution=risk_dist)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(customers, f, indent=2)
        logger.info(f"Generated {len(customers)} customers -> {args.output}")
    else:
        # Send to Kafka
        service = KafkaProducerService(
            bootstrap_servers=args.kafka_servers, topic=args.topic, generator=generator
        )
        count = service.send_batch(customers)
        logger.info(f"Sent {count} customers to Kafka")
        service.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic customer data for churn platform"
    )

    # Global arguments
    parser.add_argument(
        "--kafka-servers",
        default="localhost:9092",
        help="Kafka bootstrap servers (default: localhost:9092)",
    )
    parser.add_argument(
        "--topic",
        default="ml.predictions",
        help="Kafka topic (default: ml.predictions)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Stream command
    stream_parser = subparsers.add_parser("stream", help="Stream customers continuously")
    stream_parser.add_argument(
        "--rate", type=int, default=60, help="Customers per minute (default: 60)"
    )
    stream_parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Duration in minutes (default: infinite)",
    )
    stream_parser.add_argument("--drift", action="store_true", help="Enable drift progression")
    stream_parser.add_argument(
        "--low", type=float, default=0.5, help="Low risk proportion (default: 0.5)"
    )
    stream_parser.add_argument(
        "--medium", type=float, default=0.3, help="Medium risk proportion (default: 0.3)"
    )
    stream_parser.add_argument(
        "--high", type=float, default=0.2, help="High risk proportion (default: 0.2)"
    )

    # Drift command
    drift_parser = subparsers.add_parser("drift", help="Generate drift scenario")
    drift_parser.add_argument(
        "--duration", type=int, default=30, help="Duration in minutes (default: 30)"
    )

    # Lifecycle command
    lifecycle_parser = subparsers.add_parser("lifecycle", help="Simulate customer lifecycles")
    lifecycle_parser.add_argument(
        "--customers", type=int, default=10, help="Number of customers (default: 10)"
    )
    lifecycle_parser.add_argument(
        "--days", type=int, default=180, help="Days per lifecycle (default: 180)"
    )
    lifecycle_parser.add_argument(
        "--speed", type=int, default=60, help="Speed factor (days/sec, default: 60)"
    )

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Generate batch of customers")
    batch_parser.add_argument(
        "--count", type=int, default=100, help="Number of customers (default: 100)"
    )
    batch_parser.add_argument(
        "--output", type=str, help="Output JSON file (if not specified, sends to Kafka)"
    )
    batch_parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    batch_parser.add_argument(
        "--low", type=float, default=0.5, help="Low risk proportion (default: 0.5)"
    )
    batch_parser.add_argument(
        "--medium", type=float, default=0.3, help="Medium risk proportion (default: 0.3)"
    )
    batch_parser.add_argument(
        "--high", type=float, default=0.2, help="High risk proportion (default: 0.2)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    if args.command == "stream":
        stream_command(args)
    elif args.command == "drift":
        drift_command(args)
    elif args.command == "lifecycle":
        lifecycle_command(args)
    elif args.command == "batch":
        batch_command(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
