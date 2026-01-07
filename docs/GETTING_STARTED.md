# Getting Started with Risk/Churn Scoring Platform

This guide will help you get the platform up and running quickly.

## Prerequisites

Ensure you have the following installed:
- Python 3.11 or higher
- Docker and Docker Compose
- Git
- uv (Python package manager)

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd risk-churn-platform
```

### 2. Install Dependencies

```bash
make install-dev
```

This will:
- Create a virtual environment
- Install all dependencies
- Set up pre-commit hooks

### 3. Start Infrastructure

```bash
make docker-up
```

This starts:
- Kafka (port 9092)
- Zookeeper (port 2181)
- Redis (port 6379)
- Prometheus (port 9090)
- Grafana (port 3000)

### 4. Verify Installation

```bash
# Check services are running
docker-compose ps

# Run tests
make test
```

## Training Initial Models

Before you can make predictions, you need trained models. Here's how to train the initial models:

```python
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.risk_churn_platform.models.risk_scorer import RiskScorerV1, RiskScorerV2
from src.risk_churn_platform.transformers.feature_transformer import FeatureTransformer

# Generate sample data (replace with your actual data)
np.random.seed(42)
n_samples = 1000

data = pd.DataFrame({
    'customer_tenure': np.random.randint(1, 72, n_samples),
    'monthly_charges': np.random.uniform(20, 120, n_samples),
    'total_charges': np.random.uniform(100, 8000, n_samples),
    'contract_type': np.random.choice(['Month-to-month', 'One year', 'Two year'], n_samples),
    'payment_method': np.random.choice(['Electronic check', 'Mailed check', 'Bank transfer', 'Credit card'], n_samples),
    'internet_service': np.random.choice(['DSL', 'Fiber optic', 'No'], n_samples),
    'support_tickets': np.random.randint(0, 10, n_samples),
    'login_frequency': np.random.uniform(0, 10, n_samples),
    'label': np.random.randint(0, 2, n_samples)  # 0 = no churn, 1 = churn
})

# Split data
X = data.drop('label', axis=1)
y = data['label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize and fit transformer
feature_names = ['customer_tenure', 'monthly_charges', 'total_charges',
                 'contract_type', 'payment_method', 'internet_service',
                 'support_tickets', 'login_frequency']
transformer = FeatureTransformer(feature_names)
X_train_transformed = transformer.fit_transform(X_train)
X_test_transformed = transformer.transform(X_test)

# Train Model V1
model_v1 = RiskScorerV1()
model_v1.train(X_train_transformed, y_train.values)
model_v1.save('models/v1/model.pkl')

# Train Model V2
model_v2 = RiskScorerV2()
model_v2.train(X_train_transformed, y_train.values)
model_v2.save('models/v2/model.pkl')

print("Models trained and saved successfully!")
```

## Making Your First Prediction

### Using Python

```python
import requests

# Prediction request
response = requests.post(
    'http://localhost:8080/predict',
    json={
        'customer_tenure': 24,
        'monthly_charges': 79.99,
        'total_charges': 1919.76,
        'contract_type': 'Two year',
        'payment_method': 'Credit card',
        'internet_service': 'Fiber optic',
        'support_tickets': 2,
        'login_frequency': 5.2
    }
)

print(response.json())
```

### Using cURL

```bash
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{
    "customer_tenure": 24,
    "monthly_charges": 79.99,
    "total_charges": 1919.76,
    "contract_type": "Two year",
    "payment_method": "Credit card",
    "internet_service": "Fiber optic",
    "support_tickets": 2,
    "login_frequency": 5.2
  }'
```

Expected response:
```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "predictions": [0.35, 0.65],
  "model_version": "v1",
  "strategy": "shadow",
  "latency_ms": 12.5,
  "churn_probability": 0.65,
  "risk_score": 65.0
}
```

## Monitoring

### Prometheus Metrics

Access Prometheus at `http://localhost:9090`

Example queries:
- Predictions per second: `rate(predictions_total[5m])`
- Average latency: `rate(prediction_latency_seconds_sum[5m]) / rate(prediction_latency_seconds_count[5m])`
- Error rate: `rate(predictions_total{status="error"}[5m])`

### Grafana Dashboards

1. Open Grafana at `http://localhost:3000`
2. Login with `admin/admin`
3. Add Prometheus as a data source (URL: `http://prometheus:9090`)
4. Import dashboards from `docs/grafana-dashboards/`

### Router Metrics

Check routing performance:

```bash
# Get routing metrics
curl http://localhost:8080/router/metrics

# Shadow deployment analysis
curl http://localhost:8080/router/shadow-analysis
```

## Deployment Strategies

### Shadow Deployment (Recommended First Step)

In shadow mode, v2 runs alongside v1 but doesn't serve traffic:

```python
from src.risk_churn_platform.routers.model_router import ModelRouter, RoutingStrategy

router = ModelRouter(
    model_v1=model_v1,
    model_v2=model_v2,
    strategy=RoutingStrategy.SHADOW,
    shadow_log_predictions=True
)
```

Monitor the shadow analysis endpoint to compare v1 and v2:
```bash
curl http://localhost:8080/router/shadow-analysis
```

### Canary Release

After validating in shadow mode, gradually roll out v2:

```bash
# Start with 10% traffic to v2
# Update config.yaml:
# router:
#   strategy: "canary"
#   canary_weight: 0.1

# Restart service and monitor metrics
```

### Promote to Production

When satisfied with v2 performance:

```bash
curl -X POST http://localhost:8080/router/promote-v2
```

### Rollback

If issues arise:

```bash
curl -X POST http://localhost:8080/router/rollback
```

## Drift Detection

The platform automatically monitors for data drift:

```python
from src.risk_churn_platform.monitoring.drift_detector import DriftDetector

# Initialize detector
drift_detector = DriftDetector(
    method='ks',  # Kolmogorov-Smirnov test
    threshold=0.05,
    window_size=1000
)

# Fit on reference data
drift_detector.fit(X_reference)

# Check new data for drift
result = drift_detector.detect(X_new)

if result['is_drift']:
    print(f"Drift detected! p-value: {result['p_value']}")
```

## Retraining

### Manual Retraining

```python
from src.risk_churn_platform.deployment.retraining import RetrainingPipeline

# Initialize pipeline
pipeline = RetrainingPipeline(
    min_samples=10000,
    performance_threshold=0.85,
    auto_deploy=False
)

# Run retraining
result = pipeline.run_retraining(feedback_data, model_version='v2')

if result['ready_for_deployment']:
    print(f"Model ready! F1 Score: {result['metrics']['f1_score']}")
```

### Automated Retraining

Configure in `config/config.yaml`:

```yaml
retraining:
  enabled: true
  schedule: "0 2 * * 0"  # Weekly at 2 AM Sunday
  min_samples: 10000
  performance_threshold: 0.85
  auto_deploy: false  # Set to true for automatic deployment
```

## Common Tasks

### Add a New Feature

1. Update the feature list in `config/config.yaml`
2. Modify the transformer in `transformers/feature_transformer.py`
3. Retrain models with new features
4. Update API schema in `api/rest_api.py`

### Change Routing Strategy

```bash
# Edit config/config.yaml
router:
  strategy: "canary"  # or "shadow", "blue-green"
  canary_weight: 0.2  # 20% to v2

# Restart service
docker-compose restart api
```

### View Kafka Messages

```bash
# Install kafkacat
brew install kafkacat  # macOS
# or
apt-get install kafkacat  # Linux

# View predictions topic
kafkacat -b localhost:9092 -t ml.predictions -C

# View drift alerts
kafkacat -b localhost:9092 -t ml.drift-alerts -C
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Restart services
docker-compose down -v
docker-compose up -d
```

### Import Errors

```bash
# Reinstall dependencies
make clean
make install-dev
```

### Tests Failing

```bash
# Run specific test
pytest tests/unit/test_models.py::test_risk_scorer_v1_train_predict -v

# Run with debugging
pytest tests/ -v -s --pdb
```

### Kafka Connection Issues

```bash
# Check Kafka is running
docker-compose ps kafka

# Check topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

## Next Steps

- Read the [Architecture Guide](ARCHITECTURE.md)
- Explore the [API Documentation](http://localhost:8080/docs)
- Set up [Kubernetes Deployment](KUBERNETES.md)
- Configure [Alerting](ALERTING.md)

## Support

For issues or questions:
- GitHub Issues: [link]
- Documentation: [link]
- Community Slack: [link]
