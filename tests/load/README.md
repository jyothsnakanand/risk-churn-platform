# Load Testing

This directory contains load testing configurations for the ML platform.

## Tools

### 1. Locust (Python-based)

**Installation:**
```bash
pip install locust
```

**Run basic load test:**
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8080
```

Then open http://localhost:8089 to configure and start the test.

**Run headless (CI/CD):**
```bash
# 100 users, spawn rate of 10/sec, run for 5 minutes
locust -f tests/load/locustfile.py \
    --host=http://localhost:8080 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --html=load_test_report.html
```

**User Classes:**
- `MLPlatformUser`: Normal user behavior (prediction, health checks)
- `HighLoadUser`: Stress testing (rapid requests)
- `BurstLoadUser`: Burst traffic patterns

### 2. Artillery (Node.js-based)

**Installation:**
```bash
npm install -g artillery
```

**Run test:**
```bash
artillery run tests/load/artillery_config.yml
```

**Generate HTML report:**
```bash
artillery run --output report.json tests/load/artillery_config.yml
artillery report report.json
```

## Test Scenarios

### 1. Baseline Load Test
- **Goal**: Establish normal performance
- **Users**: 10-50 concurrent
- **Duration**: 10 minutes
- **Expected**: <50ms p95 latency, 0% errors

```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8080 \
    --users 50 \
    --spawn-rate 5 \
    --run-time 10m \
    --headless
```

### 2. Stress Test
- **Goal**: Find breaking point
- **Users**: 100-1000 concurrent
- **Duration**: 15 minutes
- **Expected**: Identify max throughput

```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8080 \
    --users 1000 \
    --spawn-rate 50 \
    --run-time 15m \
    --headless
```

### 3. Spike Test
- **Goal**: Test sudden traffic spikes
- **Pattern**: Ramp from 10 to 500 users in 1 minute
- **Expected**: System handles spike gracefully

Use Artillery configuration (includes spike phase).

### 4. Endurance Test
- **Goal**: Test for memory leaks, resource exhaustion
- **Users**: 100 concurrent
- **Duration**: 4 hours
- **Expected**: Stable performance over time

```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8080 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 4h \
    --headless
```

## Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| **Latency p50** | <10ms | <50ms |
| **Latency p95** | <50ms | <200ms |
| **Latency p99** | <100ms | <500ms |
| **Throughput** | 1000 req/s | 500 req/s |
| **Error Rate** | <0.1% | <1% |
| **CPU Usage** | <70% | <90% |
| **Memory** | <1GB | <2GB |

## Monitoring During Load Tests

### 1. System Metrics
```bash
# Monitor CPU/Memory
htop

# Monitor API server
docker stats ml-platform-api

# Monitor Kubernetes pods
kubectl top pods -n ml-platform
```

### 2. Application Metrics
```bash
# Prometheus metrics
curl http://localhost:8080/metrics

# Grafana dashboard
open http://localhost:3000
```

### 3. Logs
```bash
# Tail logs
tail -f logs/ml-platform.log

# Watch for errors
tail -f logs/ml-platform.log | grep ERROR
```

## Interpreting Results

### Good Performance
- Latency remains stable as load increases
- No errors or timeouts
- CPU/memory usage within limits
- Rate limits working correctly

### Warning Signs
- Latency increases linearly with load
- Error rate >0.1%
- Memory usage growing steadily
- High CPU usage (>80%)

### Critical Issues
- Response times >500ms
- Error rate >1%
- Service crashes or restarts
- Rate limit not working

## Optimization Tips

Based on load test results:

1. **High Latency**:
   - Profile slow code paths
   - Add caching (Redis)
   - Optimize model inference
   - Use async operations

2. **High CPU**:
   - Increase worker processes
   - Scale horizontally (more pods)
   - Optimize ML model (quantization)

3. **High Memory**:
   - Check for memory leaks
   - Reduce model size
   - Implement model caching

4. **Rate Limit Issues**:
   - Adjust rate limits per tier
   - Implement Redis-based rate limiting
   - Add rate limit monitoring

## CI/CD Integration

Add to GitHub Actions:

```yaml
- name: Run Load Test
  run: |
    # Start API server
    docker-compose up -d api

    # Wait for health check
    sleep 10

    # Run load test
    locust -f tests/load/locustfile.py \
        --host=http://localhost:8080 \
        --users 100 \
        --spawn-rate 10 \
        --run-time 2m \
        --headless \
        --html=load_test_report.html

    # Check if performance targets met
    python tests/load/check_performance.py load_test_report.html
```
