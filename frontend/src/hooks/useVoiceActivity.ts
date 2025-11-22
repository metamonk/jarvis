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
  echoCancellation: false, // Disable to prevent audio suppression
  noiseSuppression: false, // Disable to prevent zeroing out speech
  autoGainControl: false, // Disable to maintain natural volume
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
    wsUrl = `ws://${window.location.hostname}:8001/ws`,
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

  // Audio queue management for smooth playback
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const nextStartTimeRef = useRef(0);

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
   * Clear audio queue and reset playback state
   */
  const clearAudioQueue = useCallback(() => {
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    nextStartTimeRef.current = 0;
  }, []);

  /**
   * Initialize audio context
   */
  const initAudioContext = useCallback(async () => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext({ sampleRate: AUDIO_CONFIG.sampleRate });
    }

    // Ensure AudioContext is running (not suspended)
    if (audioContextRef.current.state === 'suspended') {
      console.log('[VoiceActivity] Resuming suspended AudioContext...');
      await audioContextRef.current.resume();
    }

    console.log('[VoiceActivity] AudioContext state:', audioContextRef.current.state);
    return audioContextRef.current;
  }, []);

  /**
   * Process and queue audio chunks for smooth playback
   */
  const processAudioQueue = useCallback(() => {
    const audioContext = audioContextRef.current;
    if (!audioContext || audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      setState('ready');
      return;
    }

    // Get next chunk from queue
    const audioBuffer = audioQueueRef.current.shift()!;

    // Create source and schedule it
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);

    const currentTime = audioContext.currentTime;
    const startTime = Math.max(currentTime, nextStartTimeRef.current);

    source.onended = () => {
      // Process next chunk in queue
      if (audioQueueRef.current.length > 0) {
        processAudioQueue();
      } else {
        isPlayingRef.current = false;
        setState('ready');
        console.log('[VoiceActivity] Audio queue empty, playback complete');
      }
    };

    source.start(startTime);
    nextStartTimeRef.current = startTime + audioBuffer.duration;

    console.log('[VoiceActivity] Scheduled audio chunk', {
      startTime: startTime - currentTime,
      duration: audioBuffer.duration,
      queueLength: audioQueueRef.current.length
    });
  }, []);

  /**
   * Play received audio (raw PCM 16-bit) with proper queueing
   */
  const playAudio = useCallback(async (audioData: ArrayBuffer) => {
    console.log('[VoiceActivity] Received audio chunk:', audioData.byteLength, 'bytes');

    try {
      const audioContext = await initAudioContext();

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

      // Add to queue
      audioQueueRef.current.push(audioBuffer);

      // If not currently playing, start playback
      if (!isPlayingRef.current) {
        // Stop recording to prevent audio feedback loop
        if (isRecordingRef.current) {
          console.log('[VoiceActivity] Stopping recording to prevent feedback during playback');

          // Cleanup audio nodes
          if (scriptProcessorRef.current) {
            scriptProcessorRef.current.onaudioprocess = null;
            scriptProcessorRef.current.disconnect();
            scriptProcessorRef.current = null;
          }
          if (sourceNodeRef.current) {
            sourceNodeRef.current.disconnect();
            sourceNodeRef.current = null;
          }

          // Stop media stream
          if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(track => track.stop());
            mediaStreamRef.current = null;
          }

          // Notify backend
          sendMessage({ type: 'user_stopped_speaking' });

          // Update state
          isRecordingRef.current = false;
          setIsRecording(false);
        }

        isPlayingRef.current = true;
        setState('speaking');
        nextStartTimeRef.current = audioContext.currentTime + 0.05; // Small initial delay
        processAudioQueue();
      }

      onAudioReceived?.(audioData);
    } catch (err) {
      console.error('[VoiceActivity] Failed to process audio', err);
      handleError(new Error(`Failed to process audio: ${err}`));
    }
  }, [initAudioContext, processAudioQueue, onAudioReceived, handleError, sendMessage]);

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

    // Clear audio queue
    clearAudioQueue();

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
  }, [isRecording, clearPingInterval, clearAudioQueue]);

  /**
   * Convert Float32Array to Int16Array (PCM 16-bit)
   */
  const floatTo16BitPCM = useCallback((float32Array: Float32Array): ArrayBuffer => {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);

    // Calculate max amplitude to determine if gain is needed
    let maxAmplitude = 0;
    for (let i = 0; i < float32Array.length; i++) {
      maxAmplitude = Math.max(maxAmplitude, Math.abs(float32Array[i]));
    }

    // Dynamic amplification: only amplify if signal is weak
    let amplification = 1.0;
    if (maxAmplitude > 0 && maxAmplitude < 0.1) {
      // Scale to reach ~50% of maximum (0.5) instead of clipping at 100%
      amplification = Math.min(0.5 / maxAmplitude, 4.0); // Cap at 4x to prevent extreme amplification
      console.log(`[VoiceActivity] Dynamic amplification: ${amplification.toFixed(2)}x for max amplitude ${maxAmplitude.toFixed(4)}`);
    }

    for (let i = 0; i < float32Array.length; i++) {
      // Amplify the signal with dynamic gain
      const amplified = float32Array[i] * amplification;
      // Clamp to [-1, 1] range
      const s = Math.max(-1, Math.min(1, amplified));
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

      // Verify stream is active
      console.log('[VoiceActivity] Stream active:', stream.active);
      console.log('[VoiceActivity] Audio tracks:', stream.getAudioTracks());
      stream.getAudioTracks().forEach(track => {
        console.log('[VoiceActivity] Track enabled:', track.enabled);
        console.log('[VoiceActivity] Track state:', track.readyState);
        console.log('[VoiceActivity] Track settings:', track.getSettings());
      });

      // Initialize audio context
      const audioContext = await initAudioContext();

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
        let hasSignal = false;

        for (let i = 0; i < inputData.length; i++) {
          const v = inputData[i];
          if (v < min) min = v;
          if (v > max) max = v;
          // Check if there's actual audio signal (not just noise floor)
          if (Math.abs(v) > 0.001) {
            hasSignal = true;
          }
        }

        // Skip pure silence to avoid confusing Deepgram
        if (!hasSignal) {
          console.warn('[VoiceActivity] Skipping silent audio chunk (all values < 0.001)');
          return;
        }

        // Convert Float32 to PCM 16-bit (with dynamic amplification)
        const pcmData = floatTo16BitPCM(inputData);

        // Validate PCM data isn't all zeros after conversion
        const pcmView = new Int16Array(pcmData);
        let pcmHasSignal = false;
        let pcmMax = 0;
        for (let i = 0; i < Math.min(100, pcmView.length); i++) {
          const absVal = Math.abs(pcmView[i]);
          if (absVal > 10) {  // Threshold above noise floor for 16-bit
            pcmHasSignal = true;
          }
          pcmMax = Math.max(pcmMax, absVal);
        }

        // Log first chunk and periodic updates
        if (!hasLoggedFirstChunk || Math.random() < 0.1) {  // Log 10% of chunks
          console.log(
            `[VoiceActivity] Audio stats: ${pcmData.byteLength} bytes, ` +
            `float32 range: [${min.toFixed(6)}, ${max.toFixed(6)}], ` +
            `PCM max: ${pcmMax}/32768, has signal: ${pcmHasSignal}`,
          );
          if (!hasLoggedFirstChunk) hasLoggedFirstChunk = true;
        }

        // Only send if PCM data has actual signal
        if (pcmHasSignal) {
          sendAudio(pcmData);
        } else {
          console.warn('[VoiceActivity] Skipping PCM chunk with no signal (max < 10/32768)');
        }
      };

      // Connect audio nodes
      source.connect(processor);
      processor.connect(audioContext.destination);

      // Tell the backend that a new utterance has started so it can
      // initialise any STT / VAD state.
      sendMessage({ type: 'user_started_speaking' });

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

      // Tell the backend that the current utterance has finished so
      // Deepgram can finalize and emit a final transcription.
      sendMessage({ type: 'user_stopped_speaking' });

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
