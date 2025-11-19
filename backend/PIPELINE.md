# Jarvis Pipecat Pipeline Implementation

## Overview

This implementation provides a complete **STT → LLM → TTS** voice pipeline using the Pipecat framework for the Jarvis MVP.

## Architecture

```
┌─────────────┐     ┌─────────┐     ┌─────────┐     ┌────────────┐
│   Audio In  │ --> │   STT   │ --> │   LLM   │ --> │    TTS     │ --> Audio Out
│  (Microphone)│    │(Deepgram)│    │(OpenAI) │    │(ElevenLabs)│    (Speaker)
└─────────────┘     └─────────┘     └─────────┘     └────────────┘
```

## Components

### 1. Speech-to-Text (STT) - Deepgram Nova-2
- **Location**: `src/services/deepgram_service.py`
- **Features**:
  - Real-time transcription
  - Interim results support
  - Smart formatting
  - Multi-language support (default: en-US)

### 2. Language Model (LLM) - OpenAI GPT-4 Turbo
- **Location**: `src/services/openai_service.py`
- **Features**:
  - Conversation history management
  - System prompt configuration
  - Streaming responses
  - Configurable temperature and max tokens

### 3. Text-to-Speech (TTS) - ElevenLabs Turbo v2.5
- **Location**: `src/services/elevenlabs_service.py`
- **Features**:
  - 9 preset voices (Rachel, Domi, Bella, Antoni, etc.)
  - Voice settings (stability, similarity, style)
  - Streaming optimization
  - Low latency mode

### 4. Pipeline Orchestrator
- **Location**: `src/pipeline.py`
- **Features**:
  - Complete pipeline coordination
  - Service lifecycle management
  - Conversation state management
  - Transport integration

## Installation

### 1. Install Dependencies

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the `backend/` directory:

```bash
# Required API Keys
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Optional
PINECONE_API_KEY=your_pinecone_api_key
GITHUB_TOKEN=your_github_token
COMPANY_API_KEY=your_company_api_key
```

### 3. Run Tests

```bash
python test_pipeline.py
```

## Service Initialization

### DeepgramSTTService

```python
from src.services import DeepgramSTTService
from src.config.settings import settings

stt_service = DeepgramSTTService(api_key=settings.DEEPGRAM_API_KEY)
stt = stt_service.create_service(
    model="nova-2",
    language="en-US",
    smart_format=True,
    interim_results=True
)
```

### OpenAILLMService

```python
from src.services import OpenAILLMService

llm_service = OpenAILLMService(api_key=settings.OPENAI_API_KEY)
llm = llm_service.create_service(
    model="gpt-4-turbo-preview",
    temperature=0.7,
    max_tokens=1024
)

llm_service.set_system_prompt("You are Jarvis, a helpful AI assistant.")
```

### ElevenLabsTTSService

```python
from src.services import ElevenLabsTTSService

tts_service = ElevenLabsTTSService(api_key=settings.ELEVENLABS_API_KEY)
tts = tts_service.create_service(
    voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
    model="eleven_turbo_v2_5",
    stability=0.5,
    similarity_boost=0.75,
    optimize_streaming_latency=3
)
```

## Pipeline Usage

### Basic Pipeline Setup

```python
from src.pipeline import JarvisPipeline
from pipecat.transports.base_transport import BaseTransport

# Initialize pipeline
pipeline = JarvisPipeline(
    system_prompt="You are Jarvis, a helpful assistant.",
    voice_id="21m00Tcm4TlvDq8ikWAM"
)

# Setup with transport (WebSocket, Daily, etc.)
await pipeline.setup(transport)

# Run pipeline
await pipeline.run()
```

### Advanced Usage

```python
# Change system prompt
pipeline.set_system_prompt("You are a code review assistant.")

# Clear conversation
pipeline.clear_conversation()

# Access conversation history
history = pipeline.conversation_history

# Check pipeline status
if pipeline.is_ready:
    print("Pipeline is ready!")
```

## Directory Structure

```
backend/
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py           # Configuration management
│   ├── services/
│   │   ├── __init__.py
│   │   ├── deepgram_service.py   # STT service wrapper
│   │   ├── openai_service.py     # LLM service wrapper
│   │   └── elevenlabs_service.py # TTS service wrapper
│   ├── pipeline.py               # Pipeline orchestrator
│   └── utils/                    # Utility functions
├── test_pipeline.py              # End-to-end tests
├── requirements.txt              # Python dependencies
└── PIPELINE.md                   # This file
```

## Dependencies

### Core Framework
- `pipecat-ai>=0.0.30` - Main framework
- `pipecat-ai[deepgram]` - Deepgram integration
- `pipecat-ai[openai]` - OpenAI integration
- `pipecat-ai[elevenlabs]` - ElevenLabs integration

### AI Services
- `deepgram-sdk>=3.0.0` - Speech recognition
- `openai>=1.3.0` - Language model
- `elevenlabs>=0.2.0` - Text-to-speech

### Web Framework
- `fastapi>=0.104.0` - API framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `websockets>=12.0` - WebSocket support

### Utilities
- `python-dotenv>=1.0.0` - Environment management
- `loguru>=0.7.0` - Logging
- `pydantic>=2.5.0` - Data validation
- `pydantic-settings>=2.0.0` - Settings management

## API Keys

### Deepgram
- Sign up: https://deepgram.com/
- Get API key from dashboard
- Model used: Nova-2 (optimized for real-time)

### OpenAI
- Sign up: https://platform.openai.com/
- Generate API key
- Model used: GPT-4 Turbo Preview

### ElevenLabs
- Sign up: https://elevenlabs.io/
- Get API key from profile
- Model used: Turbo v2.5 (lowest latency)

## Available Voices (ElevenLabs)

| Voice Name | Voice ID | Description |
|------------|----------|-------------|
| Rachel | `21m00Tcm4TlvDq8ikWAM` | Female, confident |
| Domi | `AZnzlk1XvdvUeBnXmlld` | Female, strong |
| Bella | `EXAVITQu4vr4xnSDxMaL` | Female, soft |
| Antoni | `ErXwobaYiN019PkySvjV` | Male, well-rounded |
| Elli | `MF3mGyEYCl7XYWbV9V6O` | Male, energetic |
| Josh | `TxGEqnHWrfWFTfGW9XjX` | Male, deep |
| Arnold | `VR6AewLTigWG4xSOukaG` | Male, crisp |
| Adam | `pNInz6obpgDQGcFmaJgB` | Male, deep |
| Sam | `yoZ06aMxZJJ28mfd3POQ` | Male, dynamic |

## Performance Targets

Based on the requirements:

- **STT Latency**: < 500ms (Deepgram Nova-2)
- **LLM Latency**: < 2s (GPT-4 Turbo with streaming)
- **TTS Latency**: < 1s (ElevenLabs Turbo v2.5)
- **Total End-to-End**: < 3.5s

## Error Handling

All service wrappers include:
- API key validation
- Service initialization checks
- Frame processing error handling
- Comprehensive logging with loguru

## Testing

The `test_pipeline.py` script validates:
1. API key configuration
2. Service initialization (STT, LLM, TTS)
3. Individual service functionality
4. End-to-end text flow (LLM → TTS)

Note: Full pipeline testing with audio requires valid API keys.

## Next Steps

1. **WebSocket Integration** (Task 3): Connect pipeline to FastAPI WebSocket endpoint
2. **Frontend Integration** (Task 4): Build React UI with audio capture
3. **Document Search** (Task 5): Add Pinecone vector search
4. **GitHub Integration** (Task 6): Add code search capabilities
5. **Company API** (Task 7): Integrate custom API endpoints

## Troubleshooting

### NLTK Data Missing
If you see NLTK errors, install required data:
```python
import nltk
nltk.download('punkt_tab')
```

### Import Errors
Ensure you're using the correct Pipecat module paths:
- Use `pipecat.services.deepgram.stt` not `pipecat.services.deepgram`
- Use `pipecat.services.openai.llm` not `pipecat.services.openai`
- Use `pipecat.services.elevenlabs.tts` not `pipecat.services.elevenlabs`

### API Rate Limits
- Deepgram: Check your plan limits
- OpenAI: Monitor token usage
- ElevenLabs: Character limits apply

## References

- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Deepgram API](https://developers.deepgram.com/)
- [OpenAI API](https://platform.openai.com/docs/)
- [ElevenLabs API](https://elevenlabs.io/docs/)

## Support

For issues specific to this implementation, check:
1. Service initialization logs
2. API key configuration
3. Pipecat version compatibility
4. Network connectivity for API calls
