"""FastAPI WebSocket server for Jarvis voice pipeline."""
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .pipeline import JarvisPipeline
from .transport import WebSocketTransport
from .config.settings import settings


# Store active connections
active_connections: Dict[str, WebSocketTransport] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Jarvis FastAPI server...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    yield

    # Shutdown
    logger.info("Shutting down Jarvis server...")
    # Close all active connections
    for connection_id, transport in list(active_connections.items()):
        try:
            await transport.cleanup()
            logger.info(f"Closed connection: {connection_id}")
        except Exception as e:
            logger.error(f"Error closing connection {connection_id}: {e}")

    active_connections.clear()
    logger.info("Server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Jarvis Voice Assistant API",
    description="Real-time voice AI assistant using Pipecat pipeline (STT → LLM → TTS)",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Jarvis Voice Assistant API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "websocket": "/ws"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        JSON with service status
    """
    # Check if required API keys are configured
    api_keys_configured = all([
        settings.DEEPGRAM_API_KEY,
        settings.OPENAI_API_KEY,
        settings.ELEVENLABS_API_KEY
    ])

    return JSONResponse(
        status_code=status.HTTP_200_OK if api_keys_configured else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "healthy" if api_keys_configured else "degraded",
            "api_keys_configured": api_keys_configured,
            "active_connections": len(active_connections)
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice communication.

    This endpoint handles bidirectional audio streaming:
    - Receives audio from client
    - Processes through STT → LLM → TTS pipeline
    - Sends synthesized audio back to client

    Protocol:
    - Client sends binary audio frames (PCM 16-bit, 16kHz, mono)
    - Server sends binary audio frames back
    - Text messages can be used for control/status
    """
    # Accept connection
    await websocket.accept()

    # Generate connection ID
    connection_id = id(websocket)
    logger.info(f"WebSocket connection accepted: {connection_id}")

    # Create transport and pipeline
    transport = None
    pipeline = None
    pipeline_task = None

    try:
        # Create WebSocket transport
        transport = WebSocketTransport(websocket)
        active_connections[str(connection_id)] = transport

        # Create pipeline instance
        pipeline = JarvisPipeline(
            system_prompt=None,  # Use default
            voice_id="21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        )

        # Setup pipeline with transport
        await pipeline.setup(transport)

        # Check if pipeline is ready
        if not pipeline.is_ready:
            logger.error("Pipeline not ready - missing API keys or configuration")
            await websocket.send_json({
                "type": "error",
                "message": "Pipeline not ready - check API configuration"
            })
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        # Send ready message to client
        await websocket.send_json({
            "type": "ready",
            "message": "Jarvis is ready to talk"
        })

        logger.info(f"Pipeline ready for connection: {connection_id}")

        # Start the pipeline in a background task
        pipeline_task = asyncio.create_task(pipeline.run())

        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive()

                # Handle different message types
                if "bytes" in message:
                    # Binary audio data
                    audio_data = message["bytes"]

                    # If using direct Deepgram, process audio directly
                    if hasattr(pipeline, 'use_direct_deepgram') and pipeline.use_direct_deepgram:
                        await pipeline.process_audio(audio_data)
                    else:
                        # Otherwise use transport
                        await transport.send_audio(audio_data)

                elif "text" in message:
                    # Text control message
                    import json
                    data = json.loads(message["text"])
                    msg_type = data.get("type")

                    if msg_type == "ping":
                        await websocket.send_json({"type": "pong"})

                    elif msg_type == "user_started_speaking":
                        # Frontend has begun capturing audio for a new utterance.
                        # Notify the pipeline so Deepgram can start any internal
                        # metrics or VAD flows.
                        if transport:
                            await transport.user_started_speaking()

                    elif msg_type == "user_stopped_speaking":
                        logger.info("📍 Received user_stopped_speaking message from frontend")
                        # Frontend has finished capturing audio for an utterance.
                        # If using direct Deepgram, finalize the speech
                        if hasattr(pipeline, 'use_direct_deepgram') and pipeline.use_direct_deepgram:
                            logger.info("🎯 Using direct Deepgram - calling finalize_speech")
                            await pipeline.finalize_speech()
                        elif transport:
                            # Otherwise notify the transport/pipeline
                            logger.info("Using transport - calling user_stopped_speaking")
                            await transport.user_stopped_speaking()

                    elif msg_type == "clear":
                        # Clear conversation history
                        pipeline.clear_conversation()
                        await websocket.send_json({
                            "type": "cleared",
                            "message": "Conversation cleared"
                        })

                    elif msg_type == "set_prompt":
                        # Update system prompt
                        new_prompt = data.get("prompt", "")
                        if new_prompt:
                            pipeline.set_system_prompt(new_prompt)
                            await websocket.send_json({
                                "type": "prompt_updated",
                                "message": "System prompt updated"
                            })

                    elif msg_type == "user_stopped_speaking":
                        # Frontend has stopped sending audio for the current
                        # utterance. Tell Deepgram to finalize so it emits a
                        # final TranscriptionFrame that we can feed into the
                        # LLM and TTS.
                        if transport:
                            await transport.user_stopped_speaking()

                    else:
                        logger.warning(f"Unknown message type: {msg_type}")

            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {connection_id}")
                break

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        logger.info(f"Client disconnected during setup: {connection_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}"
            })
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass

    finally:
        # Cleanup
        logger.info(f"Cleaning up connection: {connection_id}")

        # Stop pipeline
        if pipeline:
            try:
                await pipeline.stop()
            except Exception as e:
                logger.error(f"Error stopping pipeline: {e}")

        # Cancel pipeline task
        if pipeline_task and not pipeline_task.done():
            pipeline_task.cancel()
            try:
                await pipeline_task
            except asyncio.CancelledError:
                pass

        # Cleanup transport
        if transport:
            try:
                await transport.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up transport: {e}")

        # Remove from active connections
        if str(connection_id) in active_connections:
            del active_connections[str(connection_id)]

        logger.info(f"Connection cleanup complete: {connection_id}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
