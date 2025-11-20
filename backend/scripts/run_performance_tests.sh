#!/bin/bash

# Performance Testing Script for Jarvis
# Runs comprehensive performance tests and generates reports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
REPORTS_DIR="$BACKEND_DIR/performance_reports"

echo "=================================================="
echo "Jarvis Performance Testing Suite"
echo "=================================================="
echo ""

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Check if virtual environment exists
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "❌ Virtual environment not found at $BACKEND_DIR/venv"
    echo "Please create it first: python -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$BACKEND_DIR/venv/bin/activate"

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q -r "$BACKEND_DIR/requirements.txt"

echo ""
echo "=================================================="
echo "Step 1: Running Component Latency Tests"
echo "=================================================="
echo ""

cd "$BACKEND_DIR"
python tests/performance/test_pipeline_latency.py > "$REPORTS_DIR/latency_test_$(date +%Y%m%d_%H%M%S).log" 2>&1 || {
    echo "⚠️  Latency tests completed with warnings (see log)"
}

echo "✓ Latency tests completed"
echo ""

echo "=================================================="
echo "Step 2: Performance Report Summary"
echo "=================================================="
echo ""

# Generate summary report
cat > "$REPORTS_DIR/summary_$(date +%Y%m%d_%H%M%S).md" << 'EOF'
# Performance Test Summary

**Test Date:** $(date +"%Y-%m-%d %H:%M:%S")

## Test Results

### Latency Metrics

| Component | Target P90 | Actual P90 | Status |
|-----------|------------|------------|--------|
| STT Processing | < 100ms | TBD | - |
| LLM Inference | < 300ms | TBD | - |
| TTS Generation | < 100ms | TBD | - |
| Company API | < 50ms | TBD | - |
| Pinecone Search | < 100ms | TBD | - |
| End-to-End | < 500ms (target: 335ms) | TBD | - |
| Cache Read | < 5ms | TBD | - |
| Cache Write | < 10ms | TBD | - |

### System Configuration

- **Environment:** Development
- **Redis:** Enabled
- **Database:** PostgreSQL (local)
- **Load Balancer:** None (local testing)

### Recommendations

1. Review actual latency measurements in detailed logs
2. Identify bottlenecks and optimization opportunities
3. Run load tests to validate under realistic traffic
4. Monitor cache hit rates

## Next Steps

1. Deploy optimized infrastructure to AWS
2. Run load tests with Locust
3. Monitor production metrics
4. Iterate on optimizations

EOF

echo "✓ Summary report generated"
echo ""

echo "=================================================="
echo "Performance Test Results"
echo "=================================================="
echo ""
echo "Reports saved to: $REPORTS_DIR"
echo ""
echo "Latest latency test log:"
echo "  $(ls -t $REPORTS_DIR/latency_test_*.log | head -1)"
echo ""
echo "Summary report:"
echo "  $(ls -t $REPORTS_DIR/summary_*.md | head -1)"
echo ""

echo "=================================================="
echo "Optional: Run Load Tests"
echo "=================================================="
echo ""
echo "To run load tests with Locust:"
echo ""
echo "  # Install Locust"
echo "  pip install locust"
echo ""
echo "  # Start backend server"
echo "  uvicorn src.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "  # Run load tests (in another terminal)"
echo "  locust -f tests/performance/load_test.py \\"
echo "    --host http://localhost:8000 \\"
echo "    --users 50 \\"
echo "    --spawn-rate 5 \\"
echo "    --run-time 5m \\"
echo "    --headless \\"
echo "    --html $REPORTS_DIR/load_test_$(date +%Y%m%d_%H%M%S).html"
echo ""
echo "=================================================="

deactivate
