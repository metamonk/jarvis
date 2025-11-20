# Performance Testing Suite

This directory contains performance testing tools for the Jarvis voice assistant system.

## Overview

The performance testing suite includes:

1. **Component Latency Tests** (`test_pipeline_latency.py`)
   - Tests individual component latencies (STT, LLM, TTS)
   - Tests supporting service latencies (Company API, Pinecone)
   - Tests cache performance
   - Validates against performance targets

2. **Load Tests** (`load_test.py`)
   - Simulates realistic user load patterns
   - Measures system performance under load
   - Tracks P90/P95/P99 latencies
   - Generates HTML reports

## Performance Targets

| Component | Target P90 | Description |
|-----------|------------|-------------|
| STT (Deepgram) | < 100ms | Speech-to-Text processing |
| LLM (OpenAI) | < 300ms | Language model inference |
| TTS (ElevenLabs) | < 100ms | Text-to-Speech generation |
| Company API | < 50ms | Company data queries |
| Pinecone Search | < 100ms | Document search |
| **End-to-End** | **< 500ms (target: 335ms)** | **Complete pipeline** |
| Cache Read | < 5ms | Redis cache read operations |
| Cache Write | < 10ms | Redis cache write operations |

## Quick Start

### 1. Run Component Latency Tests

```bash
cd backend
python tests/performance/test_pipeline_latency.py
```

This will:
- Test all components individually
- Test end-to-end pipeline
- Test cache performance
- Validate against targets
- Print summary report

### 2. Run Load Tests

First, ensure the backend server is running:

```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Then run load tests (in another terminal):

```bash
# Interactive mode with web UI (http://localhost:8089)
locust -f tests/performance/load_test.py --host http://localhost:8000

# Headless mode with specific parameters
locust -f tests/performance/load_test.py \
  --host http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --headless \
  --html performance_report.html
```

### 3. Use Convenience Script

```bash
cd backend
./scripts/run_performance_tests.sh
```

This script:
- Activates virtual environment
- Installs dependencies
- Runs latency tests
- Generates reports
- Provides instructions for load testing

## Load Test Scenarios

### Light Load (Development)
```bash
locust -f tests/performance/load_test.py \
  --host http://localhost:8000 \
  --users 10 \
  --spawn-rate 2 \
  --run-time 2m \
  --headless
```

### Medium Load (Staging)
```bash
locust -f tests/performance/load_test.py \
  --host http://staging.jarvis.example.com \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --headless \
  --html reports/medium_load.html
```

### Heavy Load (Production Validation)
```bash
locust -f tests/performance/load_test.py \
  --host http://prod.jarvis.example.com \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --headless \
  --html reports/heavy_load.html
```

### Stress Test
```bash
locust -f tests/performance/load_test.py \
  --host http://prod.jarvis.example.com \
  --users 200 \
  --spawn-rate 20 \
  --run-time 10m \
  --headless \
  --html reports/stress_test.html
```

## Interpreting Results

### Latency Test Results

The latency test will output metrics like:

```
PERFORMANCE SUMMARY
===================
Total Operations: 8
Total Measurements: 800

stt_processing:
  Count: 100
  Mean: 81.23ms
  Median: 80.45ms
  P90: 85.12ms ✓ (Target: 100ms)
  P95: 87.34ms
  P99: 91.23ms
  Min: 78.01ms
  Max: 95.67ms

end_to_end:
  Count: 100
  Mean: 315.67ms
  Median: 312.34ms
  P90: 334.56ms ✓ (Target: 500ms, Goal: 335ms)
  P95: 342.89ms
  P99: 356.78ms
  Min: 298.12ms
  Max: 378.45ms

✓ All performance targets MET
```

### Load Test Results

Locust will provide:
- Requests per second (RPS)
- Response time percentiles
- Error rates
- HTML report with graphs

Key metrics to monitor:
- **P90 latency < 500ms** - Primary target
- **Error rate < 1%** - Reliability target
- **RPS capacity** - Maximum sustainable throughput

## Performance Optimization Tips

### If P90 Latency is High

1. **Check cache hit rate**
   - Low hit rate indicates caching isn't working
   - Review cache TTLs and access patterns

2. **Identify slow component**
   - Use component-specific metrics
   - Focus optimization on slowest part

3. **Review database queries**
   - Check for missing indexes
   - Look for N+1 query patterns
   - Use `EXPLAIN ANALYZE` for slow queries

4. **Check service configurations**
   - Verify using fastest models (nova-2, turbo)
   - Review optimization settings (streaming latency)

5. **Monitor resource utilization**
   - Check CPU/memory usage
   - Look for bottlenecks in ECS tasks

### If Error Rate is High

1. **Check service health**
   - Verify all services are running
   - Check API key validity
   - Review service quotas/limits

2. **Review timeouts**
   - Ensure timeouts are appropriate
   - Consider increasing for slow operations

3. **Check auto-scaling**
   - Verify ECS tasks are scaling
   - Review CloudWatch metrics

## Continuous Performance Monitoring

### In Production

1. **Set up CloudWatch Dashboards**
   - Track P90/P95/P99 latencies
   - Monitor cache hit rates
   - Track error rates

2. **Configure Alarms**
   - Alert on high latency (P90 > 500ms)
   - Alert on high error rate (> 1%)
   - Alert on cache issues

3. **Regular Performance Testing**
   - Run load tests weekly
   - Compare results over time
   - Identify performance regressions

4. **Analyze Trends**
   - Track latency trends
   - Identify performance degradation
   - Correlate with deployments

## Troubleshooting

### Tests Fail to Run

```bash
# Ensure dependencies are installed
pip install -r requirements.txt

# Ensure Redis is running (if testing cache)
redis-cli ping  # Should return "PONG"

# Check environment variables
source .env
echo $REDIS_URL
```

### Load Tests Show Connection Errors

```bash
# Verify backend is running
curl http://localhost:8000/health

# Check for port conflicts
lsof -i :8000

# Review backend logs
tail -f logs/jarvis.log
```

### High Latency in Tests but Not Production

- Tests may use simulated delays
- Production benefits from caching
- Network latency differs between environments
- Service locations matter (same AWS region)

## Contributing

When adding new tests:

1. Follow the existing test structure
2. Add appropriate assertions
3. Document expected behavior
4. Update this README

## Additional Resources

- [Performance Optimization Guide](../../PERFORMANCE_OPTIMIZATION.md)
- [Locust Documentation](https://docs.locust.io/)
- [AWS Performance Best Practices](https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/)
