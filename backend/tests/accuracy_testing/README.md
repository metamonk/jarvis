# Jarvis Accuracy and Grounding Testing

This directory contains the testing infrastructure for verifying the accuracy and grounding of Jarvis voice assistant responses.

## Objectives

1. **Accuracy**: Ensure ≥95% factual correctness of responses
2. **Grounding**: Ensure 100% of responses include proper source attribution

## Test Dataset

The test set includes **500 queries** organized into 5 categories:

### 1. Company Documentation Queries (100 queries)
- **Source**: Pinecone vector database
- **Examples**:
  - HR policies (vacation, sick leave, onboarding)
  - Safety procedures
  - Training documentation
  - IT support procedures

### 2. Load Status Queries (50 queries)
- **Source**: Company API (warehouse management system)
- **Examples**:
  - Load status and location
  - Inventory levels and reorder status
  - Equipment status and maintenance schedules

### 3. GitHub Code Search Queries (50 queries)
- **Source**: GitHub API
- **Examples**:
  - Code examples for specific technologies
  - Implementation patterns
  - Library usage examples

### 4. Edge Cases (100 queries)
- **Purpose**: Test system behavior with ambiguous or inappropriate queries
- **Examples**:
  - Empty queries
  - Out-of-scope questions
  - Malformed requests
  - Security-related queries

### 5. Multi-Turn Conversations (50 conversations, ~150 queries)
- **Purpose**: Test context retention across conversation turns
- **Examples**:
  - Follow-up questions referencing previous queries
  - Multi-step information gathering
  - Context switching between topics

## File Structure

```
accuracy_testing/
├── README.md                      # This file
├── test_queries.json              # 450-query test dataset
├── test_runner.py                 # Automated test execution script
├── calculate_accuracy.py          # Accuracy metric calculation script
└── results/                       # Test results directory
    ├── test_results_*.json        # Raw test execution results
    ├── accuracy_review_*.json     # Manual review file (to be completed)
    └── accuracy_report_*.json     # Final accuracy metrics
```

## Usage

### Step 1: Run Tests

Execute the test runner to query the system with all test queries:

```bash
cd backend/tests/accuracy_testing
python test_runner.py
```

This will:
1. Load all test queries from `test_queries.json`
2. Execute queries through the tool functions (Pinecone, Company API, GitHub)
3. Capture responses and source attributions
4. Generate two files in `results/`:
   - `test_results_TIMESTAMP.json` - Complete test execution results
   - `accuracy_review_TIMESTAMP.json` - Template for manual accuracy review

### Step 2: Manual Accuracy Review

Open the generated `accuracy_review_TIMESTAMP.json` file and review each response:

1. **Read the query and response**
2. **Verify factual correctness** against:
   - Expected behavior (for edge cases)
   - Known ground truth (for data queries)
   - Source documents (for documentation queries)
3. **Assign accuracy score** (0-10 scale):
   - `10` = Perfect, completely accurate
   - `8-9` = Good, minor issues
   - `6-7` = Acceptable, some inaccuracies
   - `0-5` = Poor, significant problems
4. **Add review notes** explaining your scoring

Example review entry:
```json
{
  "query_id": "LS-001",
  "query": "What is the status of load 2314?",
  "response": "Load 2314 status: ready_for_pickup, Location: Dock A",
  "sources": [{"type": "company_api", "system": "warehouse_management_system"}],
  "accuracy_score": 10,  // ← Add this
  "review_notes": "Response matches actual system data. Source properly attributed."  // ← Add this
}
```

### Step 3: Calculate Final Metrics

After completing the manual review, run the calculation script:

```bash
python calculate_accuracy.py results/accuracy_review_TIMESTAMP.json
```

This will:
1. Calculate overall accuracy percentage
2. Break down results by category
3. Identify problematic queries
4. Generate recommendations
5. Save a detailed report to `accuracy_report_TIMESTAMP.json`

## Expected Results

### Target Metrics

- **Accuracy**: ≥95% (average score ≥9.5/10)
- **Grounding Rate**: 100% (all responses include source attribution)

### Pass/Fail Criteria

✅ **PASS**:
- Accuracy ≥95%
- Grounding rate = 100%
- No critical errors in edge case handling

❌ **FAIL**:
- Accuracy <95%
- Grounding rate <100%
- Security concerns in edge case responses

## Test Configuration

### Running Subset Tests

To test a smaller subset during development:

```python
# In test_runner.py, modify the run_tests call:
await runner.run_tests(
    categories=['load_status', 'github_search'],  # Specific categories
    limit=10  # First 10 queries per category
)
```

### Running Full Test Suite

For production validation:

```python
await runner.run_tests(
    categories=None,  # All categories
    limit=None  # All queries
)
```

## Test Results Interpretation

### Grounding Rate

The grounding rate measures the percentage of responses that include proper source attribution:

```json
{
  "source": {
    "type": "company_api",
    "system": "warehouse_management_system",
    "endpoint": "/api/v1/loads/2314",
    "last_updated": "2025-11-19T10:30:00"
  }
}
```

**Expected**: 100% of non-error responses should have source attribution.

### Accuracy Percentage

Calculated from manual review scores:

```
Accuracy = (Sum of all scores) / (Number of reviews × 10) × 100
```

Example:
- 50 queries reviewed
- Total scores: 480
- Accuracy: 480 / (50 × 10) × 100 = 96%

### Category Breakdown

Results are broken down by category to identify specific areas needing improvement:

```
company_docs: 95.2% (48 queries)
load_status: 98.5% (50 queries)
github_search: 92.1% (45 queries)
edge_cases: 88.0% (100 queries)
multi_turn: 94.5% (150 queries)
```

## Troubleshooting

### Issue: API Connection Errors

**Symptom**: High error rate in test results

**Solution**:
1. Verify environment variables in `.env`:
   ```
   PINECONE_API_KEY=...
   COMPANY_API_URL=http://localhost:8000
   GITHUB_TOKEN=...
   ```
2. Ensure Company API is running: `python infrastructure/mock_company_api.py`
3. Check API connectivity: `curl http://localhost:8000/api/v1/loads`

### Issue: GitHub Rate Limiting

**Symptom**: GitHub search tests failing with 403 errors

**Solution**:
1. Set `GITHUB_TOKEN` in `.env` for higher rate limits
2. Reduce `limit` parameter in test runner
3. Add delays between GitHub queries:
   ```python
   await asyncio.sleep(2)  # Wait 2 seconds between requests
   ```

### Issue: Missing Pinecone Data

**Symptom**: Company docs queries return no results

**Solution**:
1. Verify Pinecone index exists and contains data
2. Check index name in `pinecone_search.py`
3. For testing without real data, company_docs tests check for source structure only

## Adding New Test Queries

To expand the test set, edit `test_queries.json`:

```json
{
  "id": "CD-101",
  "query": "What is the equipment checkout process?",
  "expected_source": "pinecone",
  "category": "Equipment Documentation"
}
```

Guidelines:
- Use sequential IDs (CD-101, LS-051, etc.)
- Specify expected source type
- Include diverse query phrasings
- Cover edge cases and ambiguous queries
- Test multi-turn conversation flows

## Continuous Testing

For ongoing quality assurance:

1. **Weekly**: Run full test suite
2. **After updates**: Run targeted category tests
3. **Before releases**: Full suite + manual review
4. **Monitor**: Track accuracy trends over time

## Future Enhancements

Potential improvements to the testing infrastructure:

1. **Automated Accuracy Scoring**: Use LLM to verify responses against ground truth
2. **Response Time Metrics**: Track query processing time
3. **Confidence Scoring**: Test system confidence in responses
4. **A/B Testing**: Compare different prompt strategies
5. **Regression Testing**: Automated checks for previously fixed issues
6. **Integration Testing**: Full end-to-end pipeline tests with voice I/O

## Contact

For questions about the testing infrastructure, refer to:
- Task Master documentation in `.taskmaster/`
- Backend pipeline documentation in `backend/PIPELINE.md`
- Tool implementation in `backend/src/tools/`
