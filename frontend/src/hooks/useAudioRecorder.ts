import { useRef, useCallback, useState, useEffect } from 'react';

/**
 * Audio recorder configuration options
 */
interface AudioRecorderConfig {
  sampleRate?: number;
  channelCount?: number;
  bufferSize?: number;
  audioLevelSmoothingFactor?: number;
}

/**
 * Audio recorder state and controls
 */
interface AudioRecorderReturn {
  isRecording: boolean;
  audioLevel: number;
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  getAudioData: () => Int16Array | null;
}

/**
 * Default configuration values
 */
const DEFAULT_CONFIG: Required<AudioRecorderConfig> = {
  sampleRate: 16000,
  channelCount: 1,
  bufferSize: 4096,
  audioLevelSmoothingFactor: 0.8,
};

/**
 * Custom hook for audio recording using Web Audio API
 *
 * Features:
 * - Microphone access with permission handling
 * - Real-time audio capture and processing
 * - Audio level monitoring with analyser node
 * - Float32Array to Int16Array conversion for streaming
 * - Automatic cleanup and resource management
 *
 * @param config - Optional configuration for audio recording
 * @param onAudioData - Callback fired when audio data is available
 * @returns Audio recorder state and control functions
 */
export const useAudioRecorder = (
  config: AudioRecorderConfig = {},
  onAudioData?: (data: Int16Array) => void
): AudioRecorderReturn => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Refs to maintain Web Audio API objects
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const analyserNodeRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const audioDataBufferRef = useRef<Int16Array | null>(null);

  // Merge config with defaults
  const finalConfig = { ...DEFAULT_CONFIG, ...config };

  /**
   * Convert Float32Array PCM data to Int16Array
   * Scales float values (-1.0 to 1.0) to 16-bit integers (-32768 to 32767)
   */
  const floatTo16BitPCM = useCallback((float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      // Clamp values to prevent overflow
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16Array;
  }, []);

  /**
   * Calculate and update audio level from analyser data
   */
  const updateAudioLevel = useCallback(() => {
    if (!analyserNodeRef.current || !isRecording) return;

    const dataArray = new Uint8Array(analyserNodeRef.current.frequencyBinCount);
    analyserNodeRef.current.getByteFrequencyData(dataArray);

    // Calculate RMS (Root Mean Square) for audio level
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i] * dataArray[i];
    }
    const rms = Math.sqrt(sum / dataArray.length);
    const normalizedLevel = rms / 255; // Normalize to 0-1

    // Apply smoothing
    setAudioLevel((prevLevel) =>
      prevLevel * finalConfig.audioLevelSmoothingFactor +
      normalizedLevel * (1 - finalConfig.audioLevelSmoothingFactor)
    );

    // Continue monitoring
    animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
  }, [isRecording, finalConfig.audioLevelSmoothingFactor]);

  /**
   * Process audio input and convert to Int16Array
   */
  const handleAudioProcess = useCallback(
    (event: AudioProcessingEvent) => {
      if (!isRecording) return;

      const inputBuffer = event.inputBuffer;
      const inputData = inputBuffer.getChannelData(0); // Mono channel

      // Convert to Int16Array
      const int16Data = floatTo16BitPCM(inputData);

      // Store latest audio data
      audioDataBufferRef.current = int16Data;

      // Call callback if provided
      if (onAudioData) {
        onAudioData(int16Data);
      }
    },
    [isRecording, floatTo16BitPCM, onAudioData]
  );

  /**
   * Start audio recording
   */
  const startRecording = useCallback(async (): Promise<void> => {
    try {
      setError(null);

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: finalConfig.channelCount,
          sampleRate: finalConfig.sampleRate,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      mediaStreamRef.current = stream;

      // Create audio context
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: finalConfig.sampleRate,
      });
      audioContextRef.current = audioContext;

      // Create source node from stream
      const sourceNode = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = sourceNode;

      // Create analyser node for audio level monitoring
      const analyserNode = audioContext.createAnalyser();
      analyserNode.fftSize = 2048;
      analyserNode.smoothingTimeConstant = 0.8;
      analyserNodeRef.current = analyserNode;

      // Create script processor for audio data extraction
      const processorNode = audioContext.createScriptProcessor(
        finalConfig.bufferSize,
        finalConfig.channelCount,
        finalConfig.channelCount
      );
      processorNodeRef.current = processorNode;
      processorNode.onaudioprocess = handleAudioProcess;

      // Connect nodes: source -> analyser -> processor -> destination
      sourceNode.connect(analyserNode);
      analyserNode.connect(processorNode);
      processorNode.connect(audioContext.destination);

      setIsRecording(true);

      // Start audio level monitoring
      updateAudioLevel();

      console.log('Audio recording started', {
        sampleRate: audioContext.sampleRate,
        channelCount: finalConfig.channelCount,
        bufferSize: finalConfig.bufferSize,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      console.error('Failed to start audio recording:', err);

      // Handle specific errors
      if (errorMessage.includes('Permission denied')) {
        setError('Microphone access denied. Please grant permission to use the microphone.');
      } else if (errorMessage.includes('NotFoundError')) {
        setError('No microphone found. Please connect a microphone and try again.');
      } else if (errorMessage.includes('NotAllowedError')) {
        setError('Microphone access not allowed. Check your browser settings.');
      } else {
        setError(`Failed to start recording: ${errorMessage}`);
      }

      // Cleanup on error
      stopRecording();
    }
  }, [finalConfig, handleAudioProcess, updateAudioLevel]);

  /**
   * Stop audio recording and cleanup resources
   */
  const stopRecording = useCallback((): void => {
    console.log('Stopping audio recording...');

    // Stop animation frame
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    // Disconnect and cleanup processor node
    if (processorNodeRef.current) {
      processorNodeRef.current.onaudioprocess = null;
      processorNodeRef.current.disconnect();
      processorNodeRef.current = null;
    }

    // Disconnect and cleanup analyser node
    if (analyserNodeRef.current) {
      analyserNodeRef.current.disconnect();
      analyserNodeRef.current = null;
    }

    // Disconnect and cleanup source node
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }

    // Stop all tracks in media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => {
        track.stop();
        console.log(`Stopped track: ${track.kind}`);
      });
      mediaStreamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close().then(() => {
        console.log('Audio context closed');
      });
      audioContextRef.current = null;
    }

    // Reset state
    setIsRecording(false);
    setAudioLevel(0);
    audioDataBufferRef.current = null;

    console.log('Audio recording stopped and resources cleaned up');
  }, []);

  /**
   * Get the latest audio data buffer
   */
  const getAudioData = useCallback((): Int16Array | null => {
    return audioDataBufferRef.current;
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (isRecording) {
        stopRecording();
      }
    };
  }, [isRecording, stopRecording]);

  return {
    isRecording,
    audioLevel,
    error,
    startRecording,
    stopRecording,
    getAudioData,
  };
};

// Type aliases for external use
export type UseAudioRecorderOptions = AudioRecorderConfig;
export type UseAudioRecorderReturn = AudioRecorderReturn;
export type RecorderState = 'idle' | 'recording' | 'paused' | 'error';
export type AudioConstraints = MediaTrackConstraints;
