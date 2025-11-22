# Jarvis Backend

Voice assistant backend using Pipecat framework for real-time voice AI pipeline.

## Technology Stack

- **Framework**: Pipecat (voice AI orchestration)
- **API Server**: FastAPI with WebSocket support
- **Language**: Python 3.12
- **ASR**: Deepgram Nova-2
- **LLM**: GPT-4 Turbo (OpenAI)
- **TTS**: ElevenLabs Turbo v2.5

## Setup

### Prerequisites

- Python 3.12 (or 3.11+)
- Virtual environment

### Installation

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
Create a `.env` file with the following variables:
```
DEEPGRAM_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here
COMPANY_API_KEY=your_key_here
```

### Running the Application

Development mode:
```bash
uvicorn jarvis_pipeline:app --reload --host 0.0.0.0 --port 8080
```

Production mode:
```bash
uvicorn jarvis_pipeline:app --host 0.0.0.0 --port 8080
```

### Testing

Run the test script to verify setup:
```bash
python test_setup.py
```

### Docker

Build:
```bash
docker build -t jarvis-backend .
```

Run:
```bash
docker run -p 8080:8080 --env-file .env jarvis-backend
```

## API Endpoints

- `GET /` - Root endpoint with service information
- `GET /health` - Health check endpoint
- `WebSocket /ws` - Main voice assistant WebSocket endpoint

## Project Structure

```
backend/
├── jarvis_pipeline.py    # Main Pipecat pipeline implementation
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── .env                 # Environment variables (not in git)
├── test_setup.py        # Setup verification script
└── README.md           # This file
```

## Development Notes

- The main implementation is in `jarvis_pipeline.py` (~250 lines)
- Custom tool functions are included for:
  - Company document search (Pinecone)
  - Load status API
  - GitHub code search
- Pipecat handles the voice pipeline orchestration
- All responses must include source attribution

## Troubleshooting

**Import errors**: Make sure virtual environment is activated and dependencies are installed

**API key errors**: Verify all required API keys are set in `.env` file

**Port conflicts**: Change the port in the uvicorn command if 8080 is in use
