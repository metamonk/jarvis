import { useState, useEffect } from 'react';
import { useVoiceActivity } from './hooks/useVoiceActivity';
import PushToTalkButton from './components/PushToTalkButton';
import { ConnectionStatus, type ConnectionStatusType } from './components/ConnectionStatus';
import AudioVisualizer from './components/AudioVisualizer';
import './App.css';

function App() {
  const [wsUrl, setWsUrl] = useState('ws://localhost:8001/ws');
  const [audioLevel, setAudioLevel] = useState(0);

  const {
    state,
    isConnected,
    isRecording,
    error,
    connect,
    disconnect,
    startRecording,
    stopRecording,
  } = useVoiceActivity({
    wsUrl,
    autoConnect: false,
    onReady: () => {
      console.log('Voice assistant ready');
    },
    onError: (err) => {
      console.error('Voice assistant error:', err);
    },
  });

  // Map voice activity state to connection status
  const getConnectionStatus = (): ConnectionStatusType => {
    if (error || state === 'error') return 'error';
    if (state === 'connecting') return 'connecting';
    if (isConnected && (state === 'ready' || state === 'recording' || state === 'processing' || state === 'speaking')) {
      return 'connected';
    }
    return 'disconnected';
  };

  const handleConnectToggle = () => {
    if (isConnected) {
      disconnect();
    } else {
      connect();
    }
  };

  // Simulate audio level based on recording state
  // In a real implementation, this would come from actual audio analysis
  const getAudioLevel = (): number => {
    if (isRecording) {
      // Simulate varying audio levels during recording
      return 30 + Math.random() * 50;
    }
    return 0;
  };

  // Update audio level periodically when recording
  useEffect(() => {
    const interval = setInterval(() => {
      if (isRecording) {
        setAudioLevel(getAudioLevel());
      } else {
        setAudioLevel(0);
      }
    }, 100);

    return () => clearInterval(interval);
  }, [isRecording]);

  const isProcessing = state === 'processing' || state === 'speaking';

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1 className="app-title">Jarvis Voice Assistant</h1>
        <ConnectionStatus
          status={getConnectionStatus()}
          errorMessage={error?.message}
        />
      </header>

      {/* Main Content */}
      <main className="app-main">
        {/* WebSocket URL Configuration */}
        <div className="connection-section">
          <label htmlFor="ws-url" className="url-label">
            WebSocket URL:
          </label>
          <div className="url-input-group">
            <input
              id="ws-url"
              type="text"
              value={wsUrl}
              onChange={(e) => setWsUrl(e.target.value)}
              disabled={isConnected}
              className="url-input"
              placeholder="ws://localhost:8001/ws"
            />
            <button
              onClick={handleConnectToggle}
              className={`connect-button ${isConnected ? 'connected' : ''}`}
              disabled={state === 'connecting'}
            >
              {state === 'connecting' ? 'Connecting...' : isConnected ? 'Disconnect' : 'Connect'}
            </button>
          </div>
        </div>

        {/* Push to Talk Button */}
        <div className="ptt-section">
          <PushToTalkButton
            onPressStart={startRecording}
            onPressEnd={stopRecording}
            isRecording={isRecording}
            isProcessing={isProcessing}
            disabled={!isConnected}
          />
        </div>

        {/* Audio Visualizer */}
        <div className="visualizer-section">
          <AudioVisualizer
            audioLevel={audioLevel}
            isActive={isRecording}
          />
        </div>

        {/* Instructions */}
        <div className="instructions-section">
          <p className="instructions-text">
            {isConnected
              ? 'Press and hold to speak or press Space bar'
              : 'Connect to start using the voice assistant'}
          </p>
          {state === 'processing' && (
            <p className="status-text">Processing your request...</p>
          )}
          {state === 'speaking' && (
            <p className="status-text">Jarvis is speaking...</p>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
