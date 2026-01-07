# Quick Start Guide - 5 Minutes to First Prediction

Get the Risk/Churn Scoring Platform running in 5 minutes with this streamlined guide.

## Prerequisites Check

```bash
# Check Python version (need 3.11+)
python3 --version

# Check Docker
docker --version

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Step 1: Clone & Setup (2 minutes)

```bash
# Clone the repository
git clone https://github.com/jyothsnakanand/risk-churn-platform.git
cd risk-churn-platform

# Install dependencies
make install-dev
```

This will:
- Create virtual environment
- Install all Python packages
- Set up pre-commit hooks

## Step 2: Start Infrastructure (1 minute)

```bash
# Start Kafka, Redis, Prometheus, Grafana
make docker-up

# Verify services are running
docker-compose ps
```

You should see:
- ✅ Kafka (port 9092)
- ✅ Zookeeper (port 2181)
- ✅ Redis (port 6379)
- ✅ Prometheus (port 9090)
- ✅ Grafana (port 3000)

## Step 3: Create & Train Models (1 minute)

Create a file `train_models.py`:

```python
import numpy as np
import pandas as pd
import os
from sklearn.model_selection import train_test_split
from src.risk_churn_platform.models.risk_scorer import RiskScorerV1, RiskScorerV2
from src.risk_churn_platform.transformers.feature_transformer import FeatureTransformer

# Create directories
os.makedirs('models/v1', exist_ok=True)
os.makedirs('models/v2', exist_ok=True)

# Generate sample data
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
    'label': np.random.randint(0, 2, n_samples)
})

# Split and transform
X = data.drop('label', axis=1)
y = data['label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

feature_names = ['customer_tenure', 'monthly_charges', 'total_charges',
                 'contract_type', 'payment_method', 'internet_service',
                 'support_tickets', 'login_frequency']
transformer = FeatureTransformer(feature_names)
X_train_transformed = transformer.fit_transform(X_train)
X_test_transformed = transformer.transform(X_test)

# Train both models
print("Training Model V1 (Random Forest)...")
model_v1 = RiskScorerV1()
model_v1.train(X_train_transformed, y_train.values, n_estimators=50)
model_v1.save('models/v1/model.pkl')

print("Training Model V2 (Gradient Boosting)...")
model_v2 = RiskScorerV2()
model_v2.train(X_train_transformed, y_train.values, n_estimators=50)
model_v2.save('models/v2/model.pkl')

# Evaluate
from sklearn.metrics import accuracy_score, f1_score
y_pred_v1 = model_v1.predict(X_test_transformed)
y_pred_v2 = model_v2.predict(X_test_transformed)

print(f"\nModel V1 - Accuracy: {accuracy_score(y_test, y_pred_v1):.3f}, F1: {f1_score(y_test, y_pred_v1):.3f}")
print(f"Model V2 - Accuracy: {accuracy_score(y_test, y_pred_v2):.3f}, F1: {f1_score(y_test, y_pred_v2):.3f}")
print("\n✅ Models trained and saved successfully!")
```

Run it:
```bash
python train_models.py
```

## Step 4: Start the API (30 seconds)

In a new terminal:

```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Start the API server
uvicorn src.risk_churn_platform.api.rest_api:app --host 0.0.0.0 --port 8080
```

Wait for: `Application startup complete.`

## Step 5: Make Your First Prediction (30 seconds)

### Option A: Using cURL

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

### Option B: Using Python

Create `test_prediction.py`:

```python
import requests

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

result = response.json()
print(f"Churn Risk: {result['risk_score']:.1f}%")
print(f"Model Used: {result['model_version']}")
print(f"Latency: {result['latency_ms']:.2f}ms")
```

Run it:
```bash
python test_prediction.py
```

### Expected Output:

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

🎉 **Congratulations!** Your prediction platform is running!

---

## What's Happening Behind the Scenes?

The platform is now running in **Shadow Mode**:
- ✅ Model V1 serves predictions to users
- ✅ Model V2 runs in parallel (not visible to users)
- ✅ Both predictions are logged for comparison
- ✅ Kafka is recording all events
- ✅ Drift detection is monitoring data quality

## Quick Monitoring Checks

### 1. API Documentation
Visit: http://localhost:8080/docs

Interactive Swagger UI with all endpoints!

### 2. Shadow Deployment Analysis
```bash
curl http://localhost:8080/router/shadow-analysis
```

See how V1 and V2 compare!

### 3. Router Metrics
```bash
curl http://localhost:8080/router/metrics
```

### 4. Prometheus
Visit: http://localhost:9090

Try query: `rate(predictions_total[5m])`

### 5. Grafana
Visit: http://localhost:3000
- Login: `admin` / `admin`
- Add Prometheus datasource: `http://prometheus:9090`

---

## Next Steps

### Test Different Deployment Strategies

#### Switch to Canary (10% traffic to V2)

Edit `config/config.yaml`:
```yaml
router:
  strategy: "canary"
  canary_weight: 0.1
```

Restart API and make 100 predictions - you'll see ~10% go to V2!

#### Promote V2 to Production

```bash
curl -X POST http://localhost:8080/router/promote-v2
```

#### Rollback if Needed

```bash
curl -X POST http://localhost:8080/router/rollback
```

### Get Prediction Explanations

```bash
curl -X POST http://localhost:8080/explain \
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

See which features drove the prediction!

### Run Tests

```bash
make test
```

### View Kafka Events

```bash
# Install kafkacat
brew install kafkacat  # macOS

# View prediction events
kafkacat -b localhost:9092 -t ml.predictions -C
```

---

## Common Commands

```bash
# Start everything
make docker-up

# Stop everything
make docker-down

# View logs
docker-compose logs -f

# Run tests
make test

# Format code
make format

# Check code quality
make lint
```

---

## Troubleshooting

### API won't start
```bash
# Check if port 8080 is in use
lsof -i :8080

# Kill any process using it
kill -9 <PID>
```

### Kafka connection errors
```bash
# Restart Kafka
docker-compose restart kafka zookeeper
```

### Import errors
```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Reinstall
make clean
make install-dev
```

### Can't find models
```bash
# Make sure you ran train_models.py
ls models/v1/model.pkl
ls models/v2/model.pkl
```

---

## Complete Example: End-to-End Test

Run this Python script to test everything:

```python
import requests
import time

# 1. Make prediction
print("1. Making prediction...")
response = requests.post('http://localhost:8080/predict', json={
    'customer_tenure': 24, 'monthly_charges': 79.99, 'total_charges': 1919.76,
    'contract_type': 'Two year', 'payment_method': 'Credit card',
    'internet_service': 'Fiber optic', 'support_tickets': 2, 'login_frequency': 5.2
})
print(f"   Risk Score: {response.json()['risk_score']:.1f}%")

# 2. Check health
print("\n2. Checking health...")
health = requests.get('http://localhost:8080/health').json()
print(f"   Status: {health['status']}")

# 3. Get metrics
print("\n3. Getting router metrics...")
metrics = requests.get('http://localhost:8080/router/metrics').json()
print(f"   V1 Requests: {metrics['v1_requests']}")
print(f"   V2 Requests: {metrics['v2_requests']}")

# 4. Shadow analysis
print("\n4. Shadow deployment analysis...")
analysis = requests.get('http://localhost:8080/router/shadow-analysis').json()
if analysis.get('comparison_count', 0) > 0:
    print(f"   Comparisons: {analysis['comparison_count']}")
    print(f"   Avg Prediction Diff: {analysis['avg_prediction_diff']:.4f}")

print("\n✅ All systems operational!")
```

---

## Learn More

- **Full Documentation**: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
- **Architecture**: [README.md](README.md)
- **Project Summary**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- **API Docs**: http://localhost:8080/docs

## Questions?

- GitHub Issues: https://github.com/jyothsnakanand/risk-churn-platform/issues
- Read the full docs in `docs/`

---

**You're all set!** 🚀 The platform is running with production-grade monitoring, A/B testing, and automated quality checks.
