# Jarvis MVP - Manual Testing Guide

Complete manual testing procedures for all implemented components.

## Prerequisites

- Python 3.11+ with venv activated
- Node.js 18+
- API keys configured in `backend/.env`
- Two terminal windows minimum

---

## Test Session 1: Backend Tool Functions (Task 3)

**Time estimate:** 10 minutes

### Step 1.1: Environment Setup

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify environment
python --version  # Should be 3.11+
pip list | grep pipecat  # Verify pipecat is installed
```

**✅ Success criteria:** Virtual environment activated, dependencies installed

### Step 1.2: Run Integration Tests

```bash
# Run all tool integration tests
python -m pytest tests/test_integration.py -v

# Expected output: 13 tests, all passing
```

**🔍 HIGHLIGHTS TO WATCH FOR:**
- ✅ All 13 tests pass (test_import_*, test_source_attribution_*)
- ✅ Tests verify: Pinecone, Company API, GitHub search functions
- ✅ Source attribution validation for each tool
- ⏱️ Should complete in < 5 seconds

### Step 1.3: Test Individual Tools

```bash
# Test Pinecone tool import
python -c "
from src.tools import search_pinecone
from src.tools.pinecone_search import PineconeSearchError
print('✅ Pinecone tool loaded successfully')
print('   - search_pinecone() function available')
print('   - PineconeSearchError exception defined')
"

# Test Company API tool
python -c "
from src.tools import get_company_data
from src.tools.company_api import CompanyAPIError
print('✅ Company API tool loaded successfully')
print('   - get_company_data() function available')
print('   - CompanyAPIError exception defined')
"

# Test GitHub search tool
python -c "
from src.tools import search_github_code
from src.tools.github_search import GitHubSearchError
print('✅ GitHub search tool loaded successfully')
print('   - search_github_code() function available')
print('   - GitHubSearchError exception defined')
"
```

**🔍 HIGHLIGHTS:**
- ✅ All three tools import without errors
- ✅ Functions are callable
- ✅ Custom error classes defined for each tool

### Step 1.4: Verify Tool Documentation

```bash
# Check README exists and is comprehensive
cat src/tools/README.md | head -50

# Verify each tool has inline docs
python -c "
from src.tools import search_pinecone, get_company_data, search_github_code
print('=== Pinecone Search Documentation ===')
print(search_pinecone.__doc__)
print('\n=== Company API Documentation ===')
print(get_company_data.__doc__)
print('\n=== GitHub Search Documentation ===')
print(search_github_code.__doc__)
"
```

**🔍 HIGHLIGHTS:**
- ✅ README.md exists with 500+ lines
- ✅ Each function has comprehensive docstrings
- ✅ Usage examples and parameter descriptions included

---

## Test Session 2: Pipecat Pipeline (Task 2)

**Time estimate:** 5 minutes

### Step 2.1: Verify API Keys

```bash
# Check all required API keys are set
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

keys = {
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
    'DEEPGRAM_API_KEY': os.getenv('DEEPGRAM_API_KEY'),
    'ELEVENLABS_API_KEY': os.getenv('ELEVENLABS_API_KEY'),
}

for key, value in keys.items():
    status = '✅' if value else '❌'
    masked = value[:8] + '...' if value else 'NOT SET'
    print(f'{status} {key}: {masked}')
"
```

**🔍 HIGHLIGHTS:**
- ✅ All three API keys should show as set
- ✅ Keys are masked (only first 8 chars shown)

### Step 2.2: Run Pipeline Tests

```bash
# Run comprehensive pipeline test suite
python test_pipeline.py
```

**🔍 HIGHLIGHTS TO WATCH FOR:**

**Phase 1: API Key Validation**
```
✅ All required API keys are present
  - OPENAI_API_KEY: Configured
  - DEEPGRAM_API_KEY: Configured
  - ELEVENLABS_API_KEY: Configured
```

**Phase 2: Service Initialization**
```
✅ STT Service initialized (Deepgram)
  - Model: nova-2
  - Features: smart_format, interim_results
✅ LLM Service initialized (OpenAI)
  - Model: gpt-4-turbo-preview
  - Streaming: Enabled
✅ TTS Service initialized (ElevenLabs)
  - Voice ID: Configured
  - Streaming: Enabled
```

**Phase 3: Pipeline Orchestration**
```
✅ JarvisPipeline created successfully
  - All services integrated
  - System prompt configured
  - Error handling enabled
```

**Phase 4: End-to-End Flow Test**
```
✅ Text flow test completed
  - Input: "Hello, how are you?"
  - LLM response generated
  - Pipeline processing successful
```

**⏱️ Expected Duration:** 5-15 seconds total
**✅ Success:** All tests pass, no errors logged

### Step 2.3: Verify Pipeline Components

```bash
# Check pipeline structure
python -c "
from src.pipeline import JarvisPipeline
from src.config.settings import settings

# Create pipeline instance
pipeline = JarvisPipeline()

print('✅ Pipeline Components Loaded:')
print(f'  - STT Service: {type(pipeline.stt_service).__name__}')
print(f'  - LLM Service: {type(pipeline.llm_service).__name__}')
print(f'  - TTS Service: {type(pipeline.tts_service).__name__}')
print(f'\n✅ Configuration:')
print(f'  - Environment: {settings.ENVIRONMENT}')
print(f'  - Log Level: {settings.LOG_LEVEL}')
"
```

**🔍 HIGHLIGHTS:**
- ✅ All three services instantiate correctly
- ✅ Settings loaded from environment
- ✅ No import errors or missing dependencies

### Step 2.4: Check Optimized Pipeline

```bash
# Test the optimized pipeline version
python -c "
from src.pipeline_optimized import JarvisPipeline
print('✅ Optimized pipeline loaded successfully')
print('   - Performance enhancements included')
print('   - Caching support available')
"
```

**🔍 HIGHLIGHTS:**
- ✅ Optimized pipeline imports successfully
- ✅ Alternative implementation available for performance testing

---

## Test Session 3: Frontend Application (Task 6)

**Time estimate:** 10 minutes

### Step 3.1: Install and Build

**Terminal 2:**
```bash
cd frontend

# Verify Node version
node --version  # Should be 18+

# Install dependencies (if needed)
npm install

# Run linter
npm run lint
```

**🔍 HIGHLIGHTS:**
- ✅ No linting errors
- ✅ TypeScript types all valid
- ⏱️ Linting completes in < 10 seconds

### Step 3.2: Build Verification

```bash
# Build for production
npm run build
```

**🔍 HIGHLIGHTS TO WATCH FOR:**

```
✅ Build successful
  - vite v5.x building for production...
  - ✓ ## modules transformed
  - dist/index.html                   X.XX kB
  - dist/assets/index-XXXXX.css       X.XX kB │ gzip: X.XX kB
  - dist/assets/index-XXXXX.js      XXX.XX kB │ gzip: XX.XX kB

✅ Bundle Analysis:
  - JavaScript bundle: ~200KB (optimized)
  - CSS bundle: ~5KB (Tailwind purged)
  - No build warnings
```

### Step 3.3: Start Development Server

```bash
# Start dev server
npm run dev
```

**🔍 HIGHLIGHTS:**

```
  VITE v5.x.x  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

**✅ Server running on http://localhost:5173**

### Step 3.4: Manual UI Testing

**Open browser to http://localhost:5173**

**🔍 UI HIGHLIGHTS TO VERIFY:**

#### Visual Elements:
- ✅ **Header**: "Jarvis Voice Assistant" title
- ✅ **Connection Status Badge**: Shows "Disconnected" (red/gray) initially
- ✅ **WebSocket URL Input**: Editable field with placeholder
- ✅ **Push-to-Talk Button**: Large circular button, centered
- ✅ **Audio Visualizer**: Canvas element below button
- ✅ **Instructions**: "Press and hold to speak" or "Press Space"

#### Interactive Testing:

**Test 1: Push-to-Talk Button States**
```
1. Default state: Gray/idle color
2. Hover: Button shows hover effect
3. Click and hold:
   - Button turns red/active
   - Text changes to "Recording..." or "Listening..."
   - Audio visualizer may show activity bars
4. Release: Returns to idle state
```

**Test 2: Keyboard Support**
```
1. Press and hold SPACE bar
   - Same behavior as click and hold
2. Release SPACE
   - Returns to idle
```

**Test 3: Connection Status**
```
1. Initial state: "Disconnected" badge (gray/red)
2. Hover over badge: Shows tooltip/status info
```

**Test 4: WebSocket URL Configuration**
```
1. Input field shows default: ws://localhost:8080/ws
2. Can be edited
3. Changes persist during session
```

**Test 5: Microphone Permission**
```
1. Click PTT button first time
2. Browser prompts for microphone permission
3. Accept permission
4. Status should show microphone access granted
```

**🔍 Console Output to Check:**
- Open browser DevTools (F12)
- Console tab should show:
  ```
  ✅ React app initialized
  ✅ Custom hooks loaded
  ✅ No error messages
  ```

### Step 3.5: Component Verification

**In browser DevTools Console:**

```javascript
// Verify React DevTools is available
// Install React DevTools browser extension if needed

// Check component tree:
// - App
//   - ConnectionStatus
//   - PushToTalkButton
//   - AudioVisualizer
```

**🔍 HIGHLIGHTS:**
- ✅ All components render
- ✅ No React warnings in console
- ✅ Hooks functioning (useWebSocket, useAudioRecorder, useVoiceActivity)

### Step 3.6: Network Testing (Without Backend)

**Expected behavior when clicking PTT without backend:**

```
1. Click/hold PTT button
2. Browser requests microphone access (first time)
3. WebSocket attempts connection to ws://localhost:8080/ws
4. Connection fails (expected - no backend running yet)
5. Status shows "Connection Failed" or "Error"
6. Console shows WebSocket error (expected)
```

**🔍 HIGHLIGHTS:**
- ✅ Error handling works gracefully
- ✅ UI doesn't crash on connection failure
- ✅ Clear error messages displayed
- ✅ Can retry connection

---

## Test Session 4: AWS Infrastructure (Task 4)

**Time estimate:** 5 minutes

### Step 4.1: CDK Setup

**Terminal 3:**
```bash
cd infrastructure

# Verify Node version
node --version

# Install dependencies
npm install

# Build TypeScript
npm run build
```

**🔍 HIGHLIGHTS:**
- ✅ TypeScript compiles without errors
- ✅ No dependency warnings
- ⏱️ Build completes in < 30 seconds

### Step 4.2: Run CDK Tests

```bash
# Run all infrastructure tests
npm run test
```

**🔍 HIGHLIGHTS TO WATCH FOR:**

```
✅ Test Suite Results:
  - VPC Configuration (3 tests)
  - ECS Cluster (2 tests)
  - RDS Database (2 tests)
  - ElastiCache Redis (2 tests)
  - Load Balancer (2 tests)
  - S3 & CloudFront (2 tests)
  - Security Groups (2 tests)

✅ All 15 tests passing
  - Test Suites: 1 passed, 1 total
  - Tests: 15 passed, 15 total
  - Snapshots: 0 total
  - Time: ~X.XXs
```

### Step 4.3: Synthesize CloudFormation

```bash
# Generate CloudFormation template
npx cdk synth
```

**🔍 HIGHLIGHTS TO WATCH FOR:**

```
✅ CDK Synthesis Successful

Resources created:
  - VPC with 6 subnets (2 AZs × 3 tiers)
  - ECS Fargate cluster
  - RDS PostgreSQL 15.4 (Multi-AZ)
  - ElastiCache Redis 7.0
  - Application Load Balancer
  - S3 bucket + CloudFront distribution
  - IAM roles (3)
  - Security groups (5)
  - Secrets Manager secret
  - CloudWatch log groups
  - ECR repository

Template size: ~XXX lines of CloudFormation
```

### Step 4.4: Verify Stack Structure

```bash
# List all resources in stack
npx cdk list

# Show what would be deployed
npx cdk diff
```

**🔍 HIGHLIGHTS:**
- ✅ Stack name: `JarvisInfrastructureStack`
- ✅ Shows resource counts
- ✅ No circular dependencies
- ✅ Cost estimation info available

---

## Test Session 5: Performance & Caching (Bonus)

**Time estimate:** 5 minutes

### Step 5.1: Test Cached Company API

**Terminal 1 (backend):**
```bash
cd backend
source venv/bin/activate

# Test the cached version of Company API
python -c "
from src.tools.company_api_cached import get_load_status_cached
print('✅ Cached Company API tool loaded')
print('   - Redis caching support available')
print('   - TTL configuration ready')
"
```

### Step 5.2: Test Performance Utilities

```bash
# Check performance monitoring tools
python -c "
from src.utils.performance import measure_latency
print('✅ Performance utilities loaded')
print('   - Latency measurement available')
print('   - Ready for P90/P95 tracking')
"
```

### Step 5.3: Check Cache Configuration

```bash
# Verify cache settings
python -c "
from src.utils.cache import get_cache_client
from src.config.settings import settings
print('✅ Cache configuration:')
print(f'   - Redis URL: {settings.REDIS_URL}')
print(f'   - TTL default: 300s')
"
```

---

## Testing Summary Checklist

### ✅ Task 3: Tool Functions
- [ ] All 13 integration tests pass
- [ ] Pinecone tool imports successfully
- [ ] Company API tool imports successfully
- [ ] GitHub search tool imports successfully
- [ ] Documentation complete and accessible

### ✅ Task 2: Pipecat Pipeline
- [ ] API keys validated
- [ ] STT service initializes (Deepgram)
- [ ] LLM service initializes (OpenAI)
- [ ] TTS service initializes (ElevenLabs)
- [ ] Pipeline orchestration works
- [ ] End-to-end text flow test passes

### ✅ Task 6: Frontend
- [ ] Lint passes with no errors
- [ ] Production build succeeds
- [ ] Dev server starts on port 5173
- [ ] All UI components render
- [ ] Push-to-talk button works (visual state changes)
- [ ] Keyboard support (Space bar) functions
- [ ] WebSocket connection attempts work
- [ ] Error handling graceful (no backend crashes)
- [ ] Microphone permission request triggers

### ✅ Task 4: Infrastructure
- [ ] TypeScript compiles successfully
- [ ] All 15 CDK tests pass
- [ ] CloudFormation synthesis succeeds
- [ ] Stack structure validated
- [ ] No circular dependencies

---

## Expected Issues (Normal Behavior)

### Frontend:
- ❌ **WebSocket connection fails**: Expected - no backend server running yet
- ⚠️ **"Connection refused"**: Normal - shows error handling works
- ⚠️ **No audio playback**: Expected - no backend to process audio

### Backend:
- ⚠️ **Test warnings about missing server**: Normal - FastAPI server tested separately
- ⚠️ **Pinecone/GitHub API errors in tests**: May occur if keys not configured (tests use mocks)

### Infrastructure:
- ⚠️ **"Bootstrap required" warning**: Normal - only needed for actual deployment
- ⚠️ **Cost warnings**: Informational - shows estimated monthly cost

---

## Next Steps After Testing

Once all tests pass:

1. **Integration**: Wire up frontend ↔ backend WebSocket connection
2. **End-to-End**: Test complete voice pipeline with real audio
3. **Performance**: Measure actual latency (target: <335ms P90)
4. **Deployment**: Deploy infrastructure to AWS
5. **Monitoring**: Set up CloudWatch dashboards

---

## Troubleshooting

### Backend tests fail:
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version
python --version  # Must be 3.11+
```

### Frontend won't build:
```bash
# Clear and reinstall
rm -rf node_modules package-lock.json
npm install
```

### CDK tests fail:
```bash
# Rebuild TypeScript
npm run build

# Check Node version
node --version  # Must be 18+
```

---

**Happy Testing! 🚀**

Report any unexpected failures or interesting findings.
