"""Tests for FastAPI WebSocket server."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.server import app
from src.transport import WebSocketTransport


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Jarvis Voice Assistant API"
    assert data["version"] == "0.1.0"
    assert "endpoints" in data
    assert "websocket" in data["endpoints"]


def test_health_check_with_api_keys(client):
    """Test health check when API keys are configured."""
    with patch("src.server.settings") as mock_settings:
        mock_settings.DEEPGRAM_API_KEY = "test_key"
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.ELEVENLABS_API_KEY = "test_key"

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["api_keys_configured"] is True
        assert "active_connections" in data


def test_health_check_without_api_keys(client):
    """Test health check when API keys are missing."""
    with patch("src.server.settings") as mock_settings:
        mock_settings.DEEPGRAM_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ELEVENLABS_API_KEY = None

        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["api_keys_configured"] is False


class TestWebSocketTransport:
    """Tests for WebSocket transport layer."""

    @pytest.mark.asyncio
    async def test_transport_initialization(self):
        """Test WebSocket transport initialization."""
        mock_websocket = AsyncMock()
        transport = WebSocketTransport(
            websocket=mock_websocket,
            sample_rate=16000,
            num_channels=1
        )

        assert transport.sample_rate == 16000
        assert transport.num_channels == 1
        assert transport.audio_format == "s16le"
        assert not transport._running

    @pytest.mark.asyncio
    async def test_transport_start_stop(self):
        """Test transport start and stop."""
        mock_websocket = AsyncMock()
        transport = WebSocketTransport(websocket=mock_websocket)

        # Start transport
        await transport.start()
        assert transport._running is True

        # Stop transport
        await transport.stop()
        assert transport._running is False

    @pytest.mark.asyncio
    async def test_transport_send_audio(self):
        """Test sending audio through transport."""
        mock_websocket = AsyncMock()
        transport = WebSocketTransport(websocket=mock_websocket)

        # Send audio data
        audio_data = b'\x00\x01' * 100
        await transport.send_audio(audio_data)

        # Should start transport automatically
        assert transport._running is True

        # Cleanup
        await transport.cleanup()

    @pytest.mark.asyncio
    async def test_transport_cleanup(self):
        """Test transport cleanup."""
        mock_websocket = AsyncMock()
        transport = WebSocketTransport(websocket=mock_websocket)

        await transport.start()
        await transport.send_audio(b'\x00\x01' * 100)

        # Cleanup
        await transport.cleanup()

        assert not transport._running
        assert transport._input_queue.empty()
        assert transport._output_queue.empty()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
