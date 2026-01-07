# Production Deployment Guide

This guide covers deploying the ML platform to production with all security and operational features enabled.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Secrets Management](#secrets-management)
5. [Database Setup](#database-setup)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Monitoring](#monitoring)
8. [Load Testing](#load-testing)
9. [Security Checklist](#security-checklist)

---

## Prerequisites

### Required Services

- **PostgreSQL 14+**: Feedback storage
- **Redis 7+**: Caching and rate limiting
- **Kafka 3+**: Event streaming
- **Kubernetes 1.28+**: Container orchestration (optional)

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit with your production values
vim .env
```

### Install Dependencies

```bash
# Core dependencies
uv pip install -e ".[production]"

# Development/testing
uv pip install -e ".[dev]"

# Kubernetes deployment
uv pip install -e ".[kubernetes]"
```

---

## Authentication

The platform uses **API Key authentication** with SHA256 hashing.

### Generate API Key

```python
from risk_churn_platform.auth import get_key_manager

manager = get_key_manager()

# Create a key for production
api_key = manager.create_key(
    name="Production Client",
    permissions=["predict", "monitor"],
    rate_limit=10000,  # 10k requests/hour
    expires_in_days=365  # 1 year expiration
)

print(f"API Key: {api_key}")
# Save this securely - it won't be shown again!
```

### Use API Key

```bash
# Include in every request
curl -X POST http://api.example.com/predict \
  -H "X-API-Key: sk_live_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Permissions

| Permission | Access |
|-----------|--------|
| `predict` | Make predictions |
| `monitor` | View metrics, router status |
| `admin` | Manage keys, promote models, rollback |

### Revoke Key

```python
manager.revoke_key(key_id="abc123")
```

---

## Rate Limiting

**Token Bucket** algorithm prevents abuse and ensures fair usage.

### Configuration

```yaml
# .env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_BURST=100
```

### Rate Limit Tiers

```python
from risk_churn_platform.middleware import AdaptiveRateLimiter

limiter = AdaptiveRateLimiter()

# Free tier: 100 req/hour
limiter.is_allowed(client_id, tier="free")

# Basic tier: 1,000 req/hour
limiter.is_allowed(client_id, tier="basic")

# Premium tier: 10,000 req/hour
limiter.is_allowed(client_id, tier="premium")

# Enterprise: 100,000 req/hour
limiter.is_allowed(client_id, tier="enterprise")
```

### Response Headers

Every response includes rate limit info:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1641234567
```

### Handle Rate Limit

```python
import requests
import time

response = requests.post(url, headers=headers, json=data)

if response.status_code == 429:
    # Rate limit exceeded
    reset_time = int(response.headers['X-RateLimit-Reset'])
    wait_seconds = reset_time - int(time.time())

    print(f"Rate limited. Retry in {wait_seconds} seconds")
    time.sleep(wait_seconds)
    # Retry request
```

---

## Secrets Management

Supports multiple backends for secure secret storage.

### Option 1: Environment Variables (Development)

```bash
# .env
DATABASE_PASSWORD=secret123
API_KEY=sk_live_...
```

```python
from risk_churn_platform.config.secrets import get_secret

password = get_secret("DATABASE_PASSWORD")
```

### Option 2: AWS Secrets Manager (Production)

```bash
# Store secret in AWS
aws secretsmanager create-secret \
    --name ml-platform/database-password \
    --secret-string "super_secret_password"

# Configure
export AWS_REGION=us-east-1
export SECRETS_BACKEND=aws
```

```python
from risk_churn_platform.config.secrets import SecretsManager, AWSSecretsBackend

manager = SecretsManager(backend=AWSSecretsBackend(region="us-east-1"))
password = manager.require("ml-platform/database-password")
```

### Option 3: HashiCorp Vault (Enterprise)

```bash
# Store secret in Vault
vault kv put secret/ml-platform/database password=super_secret_password

# Configure
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=s.abc123...
export SECRETS_BACKEND=vault
```

```python
from risk_churn_platform.config.secrets import SecretsManager, VaultSecretsBackend

manager = SecretsManager(backend=VaultSecretsBackend(
    url="https://vault.example.com",
    token="s.abc123..."
))
password = manager.require("ml-platform/database")
```

### Auto-Detection

```python
# Automatically detect backend based on environment
from risk_churn_platform.config.secrets import get_secrets_manager

manager = get_secrets_manager()
password = manager.get("DATABASE_PASSWORD", default="fallback")
```

---

## Database Setup

PostgreSQL stores predictions, feedback, and monitoring events.

### Create Database

```sql
-- Create database
CREATE DATABASE ml_platform;

-- Create user
CREATE USER ml_user WITH ENCRYPTED PASSWORD 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ml_platform TO ml_user;
```

### Initialize Schema

```python
from risk_churn_platform.database import create_db_engine, init_db

# Create engine
engine = create_db_engine(
    "postgresql://ml_user:password@localhost:5432/ml_platform",
    pool_size=10,
    max_overflow=20
)

# Create tables
init_db(engine)
```

### Store Predictions

```python
from risk_churn_platform.database import create_db_session, FeedbackRepository

session = create_db_session(engine)
repo = FeedbackRepository(session)

# Store prediction
repo.store_prediction(
    request_id="abc-123",
    features={"total_orders": 10, "total_revenue": 500.0},
    predicted_probability=0.75,
    predicted_label=1,
    risk_score=75.0,
    model_version="v1",
    routing_strategy="shadow",
    latency_ms=12.5
)
```

### Update with Feedback

```python
# When ground truth label arrives
repo.update_feedback(request_id="abc-123", actual_label=1)
```

### Get Data for Retraining

```python
# Get last 90 days of labeled data
df = repo.get_feedback_for_retraining(
    min_samples=10000,
    days_back=90,
    model_version="v1"
)

# Use for retraining
X = df.drop('label', axis=1)
y = df['label']
```

### Database Schema

See [src/risk_churn_platform/database/models.py](../src/risk_churn_platform/database/models.py) for complete schema.

**Main Tables:**
- `prediction_feedback`: Predictions and ground truth
- `model_performance`: Performance metrics over time
- `drift_events`: Drift detection events
- `outlier_events`: Outlier detection events
- `retraining_jobs`: Retraining job tracking
- `api_keys`: API key management

---

## CI/CD Pipeline

GitHub Actions workflow for automated testing and deployment.

### Workflow Steps

1. **Lint**: Ruff, Black, isort, mypy
2. **Test**: Unit tests with 88% coverage
3. **Integration Tests**: Kafka, Redis
4. **Security Scan**: Bandit, Safety
5. **Build**: Docker image
6. **Deploy Staging**: Kubernetes staging
7. **Deploy Production**: Kubernetes production with monitoring

### Required Secrets

Configure in GitHub Settings → Secrets:

```
DOCKER_USERNAME         # Docker Hub username
DOCKER_PASSWORD         # Docker Hub password or token
KUBE_CONFIG_STAGING     # Kubernetes config for staging
KUBE_CONFIG_PRODUCTION  # Kubernetes config for production
SLACK_WEBHOOK          # Slack webhook for notifications
```

### Trigger Deployment

```bash
# Push to main triggers full pipeline
git push origin main

# Manual deployment
gh workflow run ci.yml
```

### Monitor Deployment

```bash
# Watch CI/CD progress
gh run watch

# View logs
gh run view --log
```

---

## Monitoring

### Prometheus Metrics

```bash
# Scrape metrics
curl http://localhost:8080/metrics

# Key metrics:
# - predictions_total{model_version,status}
# - prediction_latency_seconds{model_version}
# - rate_limit_exceeded_total
# - drift_detected_total
```

### Grafana Dashboard

Import dashboard from [k8s/grafana-dashboard.json](../k8s/grafana-dashboard.json)

**Panels:**
- Request rate (req/s)
- Latency percentiles (p50, p95, p99)
- Error rate
- Model predictions distribution
- Drift alerts
- Rate limit violations

### Alerting Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: ml_platform
    rules:
      - alert: HighErrorRate
        expr: rate(predictions_total{status="error"}[5m]) > 0.01
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, prediction_latency_seconds) > 0.1
        annotations:
          summary: "P95 latency >100ms"

      - alert: DriftDetected
        expr: drift_detected_total > 0
        annotations:
          summary: "Data drift detected"
```

---

## Load Testing

### Locust (Python)

```bash
# Install
pip install locust

# Run load test
locust -f tests/load/locustfile.py \
    --host=http://localhost:8080 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m \
    --headless
```

### Artillery (Node.js)

```bash
# Install
npm install -g artillery

# Run test
artillery run tests/load/artillery_config.yml
```

### Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| Latency p50 | <10ms | <50ms |
| Latency p95 | <50ms | <200ms |
| Latency p99 | <100ms | <500ms |
| Throughput | 1000 req/s | 500 req/s |
| Error Rate | <0.1% | <1% |

See [tests/load/README.md](../tests/load/README.md) for detailed instructions.

---

## Security Checklist

### Before Production

- [ ] Enable HTTPS only (`HTTPS_ONLY=true`)
- [ ] Enable HSTS (`HSTS_ENABLED=true`)
- [ ] Configure CORS origins (`CORS_ORIGINS=https://app.example.com`)
- [ ] Set strong API keys (32+ char random)
- [ ] Store secrets in AWS/Vault (not .env)
- [ ] Enable rate limiting (`RATE_LIMIT_ENABLED=true`)
- [ ] Set firewall rules (allow only necessary ports)
- [ ] Enable audit logging
- [ ] Configure backup strategy
- [ ] Set up monitoring alerts
- [ ] Test disaster recovery plan

### Security Scanning

```bash
# Scan dependencies
safety check

# Scan code
bandit -r src/ -ll

# Scan Docker image
docker scan ml-platform:latest
```

### Regular Maintenance

- **Weekly**: Review access logs
- **Monthly**: Rotate API keys
- **Quarterly**: Security audit
- **Annually**: Penetration testing

---

## Troubleshooting

### High Latency

1. Check model size: `du -h models/`
2. Profile slow code: `py-spy record -- python api.py`
3. Add caching layer (Redis)
4. Scale horizontally (more pods)

### Rate Limit Issues

1. Check current limits: `GET /router/metrics`
2. Increase limits per tier
3. Implement Redis-based rate limiting
4. Add burst capacity

### Database Connection Pool Exhausted

```python
# Increase pool size
engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Default: 5
    max_overflow=40      # Default: 10
)
```

### Memory Leaks

```bash
# Monitor memory
watch -n 1 'docker stats ml-platform-api'

# Profile memory
python -m memory_profiler api.py
```

---

## Support

- **Documentation**: [docs/](../docs/)
- **Issues**: GitHub Issues
- **Slack**: #ml-platform (internal)
- **Email**: ml-platform@example.com
