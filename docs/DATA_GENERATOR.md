# Synthetic Data Generator

The data generator creates realistic e-commerce customer data with controlled patterns for:
- **Risk progression** (low → medium → high risk customers)
- **Feature drift** (gradual changes in data distribution)
- **Churn behavior** (lifecycle simulation)

## Features

### 1. **Realistic Customer Profiles**

Generates customers with three risk levels:

- **Low Risk**: Loyal, engaged customers
  - High order frequency (1.5-4.0 orders/month)
  - Recent activity (1-14 days since last order)
  - High engagement (60-95% email open rate)
  - Low cart abandonment (5-25%)
  - Few support issues

- **Medium Risk**: Warning signs appearing
  - Moderate order frequency (0.3-1.5 orders/month)
  - Some inactivity (15-45 days since last order)
  - Declining engagement (30-60% email open rate)
  - Moderate cart abandonment (35-65%)
  - Some support tickets

- **High Risk**: At risk of churning
  - Very low order frequency (0.05-0.3 orders/month)
  - Extended inactivity (45-120 days since last order)
  - Poor engagement (0-30% email open rate)
  - High cart abandonment (70-95%)
  - Multiple support issues

### 2. **Feature Drift Simulation**

Gradually shifts data distribution to simulate:
- Changing customer behavior over time
- Market trends
- Seasonal patterns
- Model degradation scenarios

### 3. **Customer Lifecycle Tracking**

Simulates individual customer journeys showing:
- Initial engagement phase
- Gradual disengagement
- Risk escalation over time
- Natural customer churn patterns

### 4. **Randomness & Variance**

Introduces realistic variation:
- Random fluctuations in metrics
- Unpredictable customer behaviors
- Natural data noise

## Usage

### Command Line Interface

The generator provides a CLI tool with multiple modes:

#### 1. **Stream Mode** - Continuous Data Generation

```bash
# Stream 60 customers per minute indefinitely
python scripts/generate_synthetic_data.py stream --rate 60

# Stream for 30 minutes with drift progression
python scripts/generate_synthetic_data.py stream --rate 120 --duration 30 --drift

# Custom risk distribution (60% low, 30% medium, 10% high)
python scripts/generate_synthetic_data.py stream --rate 60 --low 0.6 --medium 0.3 --high 0.1
```

**Options:**
- `--rate`: Customers per minute (default: 60)
- `--duration`: Minutes to run (default: infinite)
- `--drift`: Enable gradual drift progression
- `--low/--medium/--high`: Risk level proportions

#### 2. **Drift Scenario** - Demonstrate Feature Drift

```bash
# Run 30-minute drift scenario
python scripts/generate_synthetic_data.py drift --duration 30
```

This mode:
- Starts with normal distribution (50% low, 30% medium, 20% high)
- Gradually shifts to high-risk distribution (10% low, 30% medium, 60% high)
- Applies increasing drift factor to all features
- Perfect for testing drift detection algorithms

#### 3. **Lifecycle Simulation** - Customer Journeys

```bash
# Simulate 10 customers over 180 days each
python scripts/generate_synthetic_data.py lifecycle --customers 10 --days 180

# Faster simulation (120 days/sec instead of 60)
python scripts/generate_synthetic_data.py lifecycle --customers 20 --speed 120
```

Shows how individual customers degrade from low-risk to high-risk over time.

#### 4. **Batch Generation** - One-time Data Export

```bash
# Generate 1000 customers and save to JSON
python scripts/generate_synthetic_data.py batch --count 1000 --output customers.json

# Generate with custom distribution and send to Kafka
python scripts/generate_synthetic_data.py batch --count 500 --low 0.3 --medium 0.3 --high 0.4

# Reproducible generation with seed
python scripts/generate_synthetic_data.py batch --count 100 --seed 42 --output test_data.json
```

### Python API

Use the generator programmatically:

```python
from risk_churn_platform.data_generator import SyntheticDataGenerator, KafkaProducerService

# Initialize generator
generator = SyntheticDataGenerator(seed=42)

# Generate single customers
low_risk = generator.generate_customer("low")
high_risk = generator.generate_customer("high")
random_risk = generator.generate_customer()  # Random risk level

# Generate batch
customers = generator.generate_batch(
    count=100,
    risk_distribution={"low": 0.5, "medium": 0.3, "high": 0.2}
)

# Simulate customer lifecycle
lifecycle = generator.simulate_customer_lifecycle(
    customer_id="cust_123",
    duration_days=180
)

# Stream to Kafka
service = KafkaProducerService(
    bootstrap_servers="localhost:9092",
    topic="ml.predictions"
)

# Stream continuously
service.stream_customers(
    rate_per_minute=60,
    duration_minutes=10,
    drift_progression=True
)

# Or send batch
service.send_batch(customers)
```

### Controlling Drift

```python
# Set drift manually
generator.set_drift(factor=0.5, direction=1)  # 50% drift, increasing
low_risk_with_drift = generator.generate_customer("low")

# Drift makes low-risk customers worse
generator.set_drift(factor=0.8, direction=1)
degraded_customer = generator.generate_customer("low")  # More at risk

# Drift makes high-risk customers better
generator.set_drift(factor=0.5, direction=-1)
improved_customer = generator.generate_customer("high")  # Less at risk
```

## Integration with Platform

### Kafka Topics

By default, data is sent to:
- `ml.predictions` - Prediction requests and results

Configure with `--topic` flag or in code:

```bash
python scripts/generate_synthetic_data.py stream --topic custom.topic
```

### Docker Compose

Add to `docker-compose.yml`:

```yaml
data-generator:
  build:
    context: .
    dockerfile: Dockerfile.datagen
  depends_on:
    - kafka
  environment:
    KAFKA_BOOTSTRAP_SERVERS: kafka:9092
  command: ["python", "/app/scripts/generate_synthetic_data.py", "stream", "--rate", "60", "--duration", "30"]
```

Start with other services:

```bash
docker-compose up -d data-generator
```

## Use Cases

### 1. **Testing Drift Detection**

```bash
# Generate 30 minutes of drifting data
python scripts/generate_synthetic_data.py drift --duration 30
```

Monitor your drift detection system to see when it triggers alerts.

### 2. **Load Testing**

```bash
# High throughput test
python scripts/generate_synthetic_data.py stream --rate 300 --duration 10
```

Test system performance under heavy load.

### 3. **Model Training Data**

```bash
# Generate balanced training set
python scripts/generate_synthetic_data.py batch --count 10000 --output training_data.json \
  --low 0.33 --medium 0.33 --high 0.34
```

### 4. **Demo & Visualization**

```bash
# Slow stream for live demos
python scripts/generate_synthetic_data.py stream --rate 10
```

Watch predictions and metrics update in real-time on the dashboard.

### 5. **A/B Testing Simulation**

```bash
# Generate data showing model improvement
python scripts/generate_synthetic_data.py lifecycle --customers 50 --days 90
```

## Data Schema

Each generated customer includes:

### Temporal Features
- `customer_age_days`: How long they've been a customer
- `account_age_days`: Account age
- `days_since_last_order`: Recency metric

### Transaction Features
- `total_orders`: Lifetime order count
- `total_revenue`: Lifetime value
- `avg_order_value`: Average order size
- `order_frequency`: Orders per month

### Engagement Features
- `website_visits_30d`: Site visits in last 30 days
- `email_open_rate`: Email engagement (0-1)
- `cart_abandonment_rate`: Cart abandonment (0-1)
- `product_views_30d`: Product views in last 30 days

### Support Features
- `support_tickets_total`: All-time ticket count
- `support_tickets_open`: Currently open tickets
- `returns_count`: Number of returns
- `refunds_count`: Number of refunds

### Behavioral Features
- `favorite_category`: Most purchased category
- `discount_usage_rate`: How often they use discounts (0-1)
- `premium_product_rate`: Premium product purchase rate (0-1)

### Transaction Details
- `payment_method`: Payment method preference
- `shipping_method`: Shipping preference
- `failed_payment_count`: Payment failures

### Metadata
- `true_risk_level`: Ground truth label ("low", "medium", "high")
- `timestamp`: Generation timestamp
- `customer_id`: Unique identifier (lifecycle mode)
- `drift_progress`: Drift progression (drift mode)

## Configuration

### Kafka Settings

Configure Kafka connection:

```bash
export KAFKA_BOOTSTRAP_SERVERS="kafka1:9092,kafka2:9092"
python scripts/generate_synthetic_data.py stream --kafka-servers $KAFKA_BOOTSTRAP_SERVERS
```

### Risk Distributions

Customize the mix of customers:

```python
# Mostly high-risk customers (stress test)
risk_dist = {"low": 0.1, "medium": 0.2, "high": 0.7}

# Balanced distribution (realistic)
risk_dist = {"low": 0.4, "medium": 0.4, "high": 0.2}

# Optimistic distribution (healthy business)
risk_dist = {"low": 0.7, "medium": 0.2, "high": 0.1}
```

### Generation Rates

Recommended rates for different scenarios:

- **Development/Testing**: 10-30 customers/min
- **Demo**: 30-60 customers/min
- **Load Testing**: 100-500 customers/min
- **Stress Testing**: 500+ customers/min

## Monitoring

Monitor the generator:

```bash
# Check Kafka topic
docker exec -it risk-churn-platform-kafka-1 kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ml.predictions \
  --from-beginning \
  --max-messages 10

# View logs
docker-compose logs -f data-generator
```

## Troubleshooting

### Can't connect to Kafka

```bash
# Check Kafka is running
docker-compose ps kafka

# Test connection
docker exec -it risk-churn-platform-kafka-1 kafka-topics --list --bootstrap-server localhost:9092
```

### Script not executable

```bash
chmod +x scripts/generate_synthetic_data.py
```

### Import errors

Ensure the package is installed:

```bash
pip install -e .
```

## Examples

### Quick Start

```bash
# 1. Start platform
docker-compose up -d

# 2. Generate data for 5 minutes
python scripts/generate_synthetic_data.py stream --rate 60 --duration 5

# 3. Watch dashboard at http://localhost
```

### Drift Detection Demo

```bash
# Generate 60 minutes of gradually drifting data
python scripts/generate_synthetic_data.py drift --duration 60

# Monitor drift detection alerts in:
# - Dashboard: http://localhost
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
```

### Customer Journey Analysis

```bash
# Simulate 100 customer lifecycles
python scripts/generate_synthetic_data.py lifecycle --customers 100 --days 365 --speed 120

# Analyze patterns in dashboard
```

## Next Steps

- Monitor real-time predictions in the [Dashboard](http://localhost)
- View Prometheus metrics at http://localhost:9090
- Explore Grafana dashboards at http://localhost:3000
- Check API documentation at http://localhost:8000/docs
