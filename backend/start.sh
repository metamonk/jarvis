#!/bin/bash
# Load environment variables from .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Use PORT from .env, default to 8000
PORT=${PORT:-8000}

echo "Starting Jarvis backend on port $PORT..."
uvicorn src.server:app --reload --host 0.0.0.0 --port $PORT
