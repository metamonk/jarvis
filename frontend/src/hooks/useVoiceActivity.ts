/**
 * useVoiceActivity Hook
 *
 * Orchestrates WebSocket connection and audio recording for voice interaction.
 * Manages the complete voice activity lifecycle: connection, recording, processing, and playback.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// Voice activity states
export type VoiceActivityState = 'idle' | 'connecting' | 'ready' | 'recording' | 'processing' | 'speaking' | 'error';

// WebSocket message types
interface WebSocketMessage {
  type: string;
  message?: string;
  prompt?: string;
}

// Unused interface declarations - commented out
// interface ReadyMessage extends WebSocketMessage {
//   type: 'ready';
// }

// interface ErrorMessage extends WebSocketMessage {
//   type: 'error';
// }

// interface ClearedMessage extends WebSocketMessage {
//   type: 'cleared';
// }

// interface PromptUpdatedMessage extends WebSocketMessage {
//   type: 'prompt_updated';
// }

// Audio configuration
const AUDIO_CONFIG = {
  sampleRate: 16000, // 16kHz as expected by backend
  channelCount: 1, // Mono
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
};

// WebSocket configuration
const WS_CONFIG = {
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  pingInterval: 30000,
};

export interface UseVoiceActivityOptions {
  wsUrl?: string;
  autoConnect?: boolean;
  onReady?: () => void;
  onError?: (error: Error) => void;
  onAudioReceived?: (audio: ArrayBuffer) => void;
}

export interface UseVoiceActivityReturn {
  state: VoiceActivityState;
  isConnected: boolean;
  isRecording: boolean;
  error: Error | null;
  connect: () => void;
  disconnect: () => void;
  startRecording: () => void;
  stopRecording: () => void;
  clearConversation: () => void;
  setSystemPrompt: (prompt: string) => void;
}

/**
 * Custom hook for managing voice activity with WebSocket and audio recording
 */
export function useVoiceActivity(options: UseVoiceActivityOptions = {}): UseVoiceActivityReturn {
  const {
    wsUrl = `ws://${window.location.hostname}:8000/ws`,
    autoConnect = false,
    onReady,
    onError,
    onAudioReceived,
  } = options;

  // State
  const [state, setState] = useState<VoiceActivityState>('idle');
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const isRecordingRef = useRef(false); // Ref to avoid closure issues in onaudioprocess

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null);
    if (state === 'error') {
      setState('idle');
    }
  }, [state]);

  /**
   * Handle errors
   */
  const handleError = useCallback((err: Error) => {
    console.error('Voice activity error:', err);
    setError(err);
    setState('error');
    onError?.(err);
  }, [onError]);

  /**
   * Send JSON message over WebSocket
   */
  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  /**
   * Send audio data over WebSocket
   */
  const sendAudio = useCallback((audioData: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(audioData);
    }
  }, []);

  /**
   * Setup ping interval to keep connection alive
   */
  const setupPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }

    pingIntervalRef.current = setInterval(() => {
      sendMessage({ type: 'ping' });
    }, WS_CONFIG.pingInterval) as unknown as number;
  }, [sendMessage]);

  /**
   * Clear ping interval
   */
  const clearPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  /**
   * Initialize audio context
   */
  const initAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext({ sampleRate: AUDIO_CONFIG.sampleRate });
    }
    return audioContextRef.current;
  }, []);

  /**
   * Play received audio (raw PCM 16-bit)
   */
  const playAudio = useCallback(async (audioData: ArrayBuffer) => {
    // Debug hook: log every time we receive audio from the backend
    console.log('[VoiceActivity] Received audio from backend:', audioData.byteLength, 'bytes');

    try {
      const audioContext = initAudioContext();
      console.log('[VoiceActivity] AudioContext state:', audioContext.state);

      // Convert PCM 16-bit to Float32Array
      const pcmData = new Int16Array(audioData);
      const floatData = new Float32Array(pcmData.length);

      // Convert from 16-bit int to float (-1 to 1)
      for (let i = 0; i < pcmData.length; i++) {
        floatData[i] = pcmData[i] / 32768.0;
      }

      // Create AudioBuffer
      const audioBuffer = audioContext.createBuffer(
        1, // mono
        floatData.length,
        AUDIO_CONFIG.sampleRate || 16000
      );

      // Copy data to buffer
      audioBuffer.copyToChannel(floatData, 0);

      console.log('[VoiceActivity] Created AudioBuffer', {
        length: audioBuffer.length,
        duration: audioBuffer.duration,
        sampleRate: audioBuffer.sampleRate,
      });

      // Create source and play
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);

      // Update state to speaking
      setState('speaking');

      source.onended = () => {
        console.log('[VoiceActivity] Playback finished');
        setState('ready');
      };

      source.start(0);
      console.log('[VoiceActivity] Playback started');
      onAudioReceived?.(audioData);
    } catch (err) {
      console.error('[VoiceActivity] Failed to play audio', err);
      handleError(new Error(`Failed to play audio: ${err}`));
    }
  }, [initAudioContext, onAudioReceived, handleError]);

  /**
   * Handle WebSocket messages
   */
  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    // Handle binary audio data
    if (event.data instanceof ArrayBuffer) {
      playAudio(event.data);
      return;
    }

    // Handle blob audio data
    if (event.data instanceof Blob) {
      event.data.arrayBuffer().then(playAudio);
      return;
    }

    // Handle text messages
    if (typeof event.data === 'string') {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        switch (message.type) {
          case 'ready':
            setState('ready');
            setIsConnected(true);
            reconnectAttemptsRef.current = 0;
            setupPingInterval();
            onReady?.();
            break;

          case 'pong':
            // Keep-alive response
            break;

          case 'cleared':
            console.log('Conversation cleared');
            break;

          case 'prompt_updated':
            console.log('System prompt updated');
            break;

          case 'error':
            handleError(new Error(message.message || 'Unknown error from server'));
            break;

          default:
            console.warn('Unknown message type:', message.type);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    }
  }, [playAudio, setupPingInterval, onReady, handleError]);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log('Already connected or connecting');
      return;
    }

    clearError();
    setState('connecting');

    try {
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        console.log('WebSocket connected');
        wsRef.current = ws;
      };

      ws.onmessage = handleWebSocketMessage;

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        handleError(new Error('WebSocket connection error'));
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        clearPingInterval();

        // Attempt reconnection if not a normal closure
        if (event.code !== 1000 && reconnectAttemptsRef.current < WS_CONFIG.maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`Attempting reconnection (${reconnectAttemptsRef.current}/${WS_CONFIG.maxReconnectAttempts})...`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, WS_CONFIG.reconnectInterval) as unknown as number;
        } else if (reconnectAttemptsRef.current >= WS_CONFIG.maxReconnectAttempts) {
          handleError(new Error('Max reconnection attempts reached'));
        } else {
          setState('idle');
        }
      };

      wsRef.current = ws;
    } catch (err) {
      handleError(new Error(`Failed to connect: ${err}`));
    }
  }, [wsUrl, clearError, handleWebSocketMessage, clearPingInterval, handleError]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    // Clear reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Clear ping interval
    clearPingInterval();

    // Stop recording if active
    if (isRecording) {
      stopRecording();
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
    setState('idle');
    reconnectAttemptsRef.current = 0;
  }, [isRecording, clearPingInterval]);

  /**
   * Convert Float32Array to Int16Array (PCM 16-bit)
   */
  const floatTo16BitPCM = useCallback((float32Array: Float32Array): ArrayBuffer => {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);

    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return buffer;
  }, []);


  /**
   * Start recording audio
   */
  const startRecording = useCallback(async () => {
    if (!isConnected) {
      handleError(new Error('Not connected to server'));
      return;
    }

    if (isRecording) {
      console.log('Already recording');
      return;
    }

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: AUDIO_CONFIG,
      });

      mediaStreamRef.current = stream;

      // Initialize audio context
      const audioContext = initAudioContext();

      // Create audio source from stream
      const source = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      // Create ScriptProcessorNode for real-time audio processing
      // Buffer size: 4096 samples at 16kHz = ~256ms per chunk
      const bufferSize = 4096;
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);
      scriptProcessorRef.current = processor;

      // Track if we've logged the first chunk
      let hasLoggedFirstChunk = false;

      // Process audio in real-time
      processor.onaudioprocess = (e) => {
        // Use ref to check current recording state (avoids closure issues)
        if (!isRecordingRef.current) return;

        // Get input audio data
        const inputData = e.inputBuffer.getChannelData(0);

        // Debug: inspect raw microphone samples to ensure we're not just
        // capturing silence from the browser.
        let min = 1.0;
        let max = -1.0;
        for (let i = 0; i < inputData.length; i++) {
          const v = inputData[i];
          if (v < min) min = v;
          if (v > max) max = v;
        }

        // Convert Float32 to PCM 16-bit
        const pcmData = floatTo16BitPCM(inputData);

        // Log first chunk to verify audio is being sent
        if (!hasLoggedFirstChunk) {
          console.log(
            `Sending audio chunk: ${pcmData.byteLength} bytes (mic min=${min.toFixed(
              6,
            )}, max=${max.toFixed(6)})`,
          );
          hasLoggedFirstChunk = true;
        }

        // Send chunk to server immediately
        sendAudio(pcmData);
      };

      // Connect audio nodes
      source.connect(processor);
      processor.connect(audioContext.destination);

      // Update both state and ref
      isRecordingRef.current = true;
      setIsRecording(true);
      setState('recording');

      console.log('Recording started with real-time streaming');
    } catch (err) {
      handleError(new Error(`Failed to start recording: ${err}`));
    }
  }, [isConnected, isRecording, initAudioContext, floatTo16BitPCM, sendAudio, handleError]);

  /**
   * Stop recording audio
   */
  const stopRecording = useCallback(() => {
    if (!isRecording) {
      console.log('Not currently recording');
      return;
    }

    try {
      // Disconnect and cleanup audio nodes
      if (scriptProcessorRef.current) {
        scriptProcessorRef.current.onaudioprocess = null;
        scriptProcessorRef.current.disconnect();
        scriptProcessorRef.current = null;
      }

      if (sourceNodeRef.current) {
        sourceNodeRef.current.disconnect();
        sourceNodeRef.current = null;
      }

      // Stop media stream tracks
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
        mediaStreamRef.current = null;
      }

      // Update both state and ref
      isRecordingRef.current = false;
      setIsRecording(false);
      setState('processing');

      console.log('Recording stopped');
    } catch (err) {
      handleError(new Error(`Failed to stop recording: ${err}`));
    }
  }, [isRecording, handleError]);

  /**
   * Clear conversation history
   */
  const clearConversation = useCallback(() => {
    sendMessage({ type: 'clear' });
  }, [sendMessage]);

  /**
   * Set system prompt
   */
  const setSystemPrompt = useCallback((prompt: string) => {
    sendMessage({ type: 'set_prompt', prompt });
  }, [sendMessage]);

  /**
   * Auto-connect on mount if enabled
   */
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      disconnect();

      // Close audio context
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, [autoConnect]); // Only run on mount

  return {
    state,
    isConnected,
    isRecording,
    error,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    clearConversation,
    setSystemPrompt,
  };
}
