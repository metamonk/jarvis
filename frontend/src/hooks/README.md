# Frontend Hooks

Custom React hooks for managing voice interaction in the Jarvis application.

## Hooks Overview

### `useVoiceActivity` (Recommended)

The main orchestration hook that combines WebSocket and audio recording for complete voice interaction.

**Features:**
- WebSocket connection management with auto-reconnect
- Audio recording from microphone
- Audio transmission to server
- Audio playback from server
- Voice activity state management
- Conversation control (clear history, set prompts)

**Usage:**

```typescript
import { useVoiceActivity } from './hooks';

function VoiceChat() {
  const {
    state,
    isConnected,
    isRecording,
    error,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    clearConversation,
  } = useVoiceActivity({
    wsUrl: 'ws://localhost:8001/ws',
    autoConnect: true,
    onReady: () => console.log('Ready to talk!'),
    onError: (err) => console.error('Error:', err),
  });

  return (
    <div>
      <p>State: {state}</p>
      {!isConnected && <button onClick={connect}>Connect</button>}
      {isConnected && !isRecording && (
        <button onClick={startRecording}>Start Recording</button>
      )}
      {isRecording && (
        <button onClick={stopRecording}>Stop Recording</button>
      )}
      {error && <p>Error: {error.message}</p>}
    </div>
  );
}
```

### `useWebSocket`

Low-level WebSocket connection hook for custom implementations.

**Features:**
- WebSocket connection management
- Auto-reconnection with configurable attempts
- Keep-alive ping mechanism
- Binary and text data support
- Connection state tracking

**Usage:**

```typescript
import { useWebSocket } from './hooks';

function CustomWebSocket() {
  const { isConnected, send, sendJSON } = useWebSocket({
    url: 'ws://localhost:8001/ws',
    autoConnect: true,
    onMessage: (event) => {
      console.log('Received:', event.data);
    },
  });

  const sendMessage = () => {
    sendJSON({ type: 'ping' });
  };

  return (
    <div>
      <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
      <button onClick={sendMessage}>Send Ping</button>
    </div>
  );
}
```

### `useAudioRecorder`

Audio recording hook for capturing microphone input.

**Features:**
- MediaRecorder API integration
- Configurable audio constraints
- Recording state management
- Pause/resume support
- Audio data callbacks

**Usage:**

```typescript
import { useAudioRecorder } from './hooks';

function AudioRecorder() {
  const {
    isRecording,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
  } = useAudioRecorder({
    audioConstraints: {
      sampleRate: 16000,
      channelCount: 1,
    },
    onDataAvailable: (blob) => {
      console.log('Audio chunk:', blob);
    },
  });

  return (
    <div>
      <button onClick={() => startRecording()}>Start</button>
      <button onClick={stopRecording}>Stop</button>
      {isRecording && (
        <>
          <button onClick={pauseRecording}>Pause</button>
          <button onClick={resumeRecording}>Resume</button>
        </>
      )}
    </div>
  );
}
```

## State Machines

### VoiceActivityState

```
idle → connecting → ready → recording → processing → speaking → ready
                            ↓
                          error
```

- **idle**: Not connected
- **connecting**: Establishing WebSocket connection
- **ready**: Connected and ready for interaction
- **recording**: Capturing audio from microphone
- **processing**: Server processing audio (STT → LLM)
- **speaking**: Playing audio response (TTS)
- **error**: Error occurred

### WebSocketState

```
disconnected → connecting → connected
               ↓
             error
```

### RecorderState

```
idle → recording → paused → recording → idle
       ↓
     error
```

## WebSocket Protocol

### Client → Server

**Audio Data (Binary)**
```
ArrayBuffer (PCM 16-bit, 16kHz, mono)
```

**Control Messages (JSON)**
```json
// Ping
{ "type": "ping" }

// Clear conversation
{ "type": "clear" }

// Set system prompt
{ "type": "set_prompt", "prompt": "You are..." }
```

### Server → Client

**Audio Data (Binary)**
```
ArrayBuffer (audio response)
```

**Status Messages (JSON)**
```json
// Ready
{ "type": "ready", "message": "Jarvis is ready to talk" }

// Pong
{ "type": "pong" }

// Cleared
{ "type": "cleared", "message": "Conversation cleared" }

// Prompt updated
{ "type": "prompt_updated", "message": "System prompt updated" }

// Error
{ "type": "error", "message": "Error description" }
```

## Audio Configuration

Default audio settings optimized for speech:

```typescript
{
  sampleRate: 16000,      // 16kHz (optimal for STT)
  channelCount: 1,        // Mono
  echoCancellation: true, // Remove echo
  noiseSuppression: true, // Remove background noise
  autoGainControl: true,  // Normalize volume
}
```

## Browser Compatibility

- **WebSocket**: All modern browsers
- **MediaRecorder**: Chrome 49+, Firefox 25+, Safari 14.1+
- **AudioContext**: All modern browsers

## Error Handling

All hooks provide error state and callbacks:

```typescript
const { error, state } = useVoiceActivity({
  onError: (err) => {
    // Handle error
    console.error('Voice activity error:', err);

    // Show user-friendly message
    if (err.message.includes('Permission denied')) {
      alert('Please allow microphone access');
    }
  },
});

// Check error state
if (error) {
  console.log('Current error:', error.message);
}

// Check for error state
if (state === 'error') {
  // Show error UI
}
```

## Performance Tips

1. **Auto-connect**: Only use when immediately needed
```typescript
useVoiceActivity({ autoConnect: false }); // Better
```

2. **Cleanup**: Hooks automatically cleanup on unmount

3. **Reconnection**: Configure based on network reliability
```typescript
useWebSocket({
  reconnectInterval: 5000,  // Longer for stable networks
  maxReconnectAttempts: 3,  // Fewer attempts
});
```

4. **Audio buffering**: Server handles streaming, no client buffering needed

## Testing

### Manual Testing

1. Start backend server:
```bash
cd backend
python -m src.server
```

2. Test connection:
```typescript
const { connect, isConnected } = useVoiceActivity();
connect();
// Should see: WebSocket connected
```

3. Test recording:
```typescript
startRecording();
// Should request microphone permission
// Should see: Recording started
```

### Integration Testing

```typescript
import { renderHook, act } from '@testing-library/react';
import { useVoiceActivity } from './hooks';

test('should connect and record', async () => {
  const { result } = renderHook(() => useVoiceActivity());

  await act(async () => {
    result.current.connect();
  });

  expect(result.current.isConnected).toBe(true);

  await act(async () => {
    await result.current.startRecording();
  });

  expect(result.current.isRecording).toBe(true);
});
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              useVoiceActivity                   │
│  (High-level orchestration)                     │
├─────────────────────────────────────────────────┤
│  • Connection management                        │
│  • Recording coordination                       │
│  • State management                             │
│  • Audio processing                             │
└──────────┬──────────────────────┬───────────────┘
           │                      │
    ┌──────▼──────┐        ┌──────▼──────────┐
    │ useWebSocket │        │ useAudioRecorder │
    │              │        │                  │
    │ • Connect    │        │ • Record         │
    │ • Send/Recv  │        │ • Pause/Resume   │
    │ • Reconnect  │        │ • Audio chunks   │
    └──────────────┘        └──────────────────┘
```

## Next Steps

1. Implement UI components using these hooks
2. Add visual feedback for voice activity
3. Add volume meter during recording
4. Add conversation history display
5. Add settings panel for audio configuration
