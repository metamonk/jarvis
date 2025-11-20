#!/bin/bash
# Quick start script for running accuracy and grounding tests

set -e

echo "========================================"
echo "Jarvis Accuracy & Grounding Test Runner"
echo "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "test_queries.json" ]; then
    echo "Error: test_queries.json not found."
    echo "Please run this script from the accuracy_testing directory:"
    echo "  cd backend/tests/accuracy_testing"
    echo "  ./run_tests.sh"
    exit 1
fi

# Check if Python virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment detected."
    echo "Activating backend virtual environment..."
    source ../../../venv/bin/activate
fi

# Check if required packages are installed
echo "Checking dependencies..."
python -c "import httpx, loguru" 2>/dev/null || {
    echo "Error: Required packages not installed."
    echo "Installing dependencies..."
    pip install httpx loguru
}

# Create results directory if it doesn't exist
mkdir -p results

echo ""
echo "Starting test execution..."
echo "This may take several minutes depending on the number of queries."
echo ""

# Run the tests
python test_runner.py

echo ""
echo "========================================"
echo "Test execution complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Review the generated accuracy_review_*.json file in results/"
echo "2. Add accuracy scores (0-10) and review notes for each query"
echo "3. Run: python calculate_accuracy.py results/accuracy_review_*.json"
echo ""
echo "Files generated in results/:"
ls -lh results/ | tail -n 5
echo ""
