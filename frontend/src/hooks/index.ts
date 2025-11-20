/**
 * Hooks Index
 *
 * Central export point for all custom React hooks
 */

// WebSocket Hook
export { useWebSocket, ConnectionState } from './useWebSocket';
export type {
  WebSocketConfig,
  ConnectionState as ConnectionStateType,
  UseWebSocketReturn,
  WebSocketState,
  UseWebSocketOptions,
} from './useWebSocket';

// Audio Recorder Hook
export { useAudioRecorder } from './useAudioRecorder';
export type {
  UseAudioRecorderOptions,
  UseAudioRecorderReturn,
  RecorderState,
  AudioConstraints,
} from './useAudioRecorder';

// Voice Activity Hook
export { useVoiceActivity } from './useVoiceActivity';
export type {
  VoiceActivityState,
  UseVoiceActivityOptions,
  UseVoiceActivityReturn,
} from './useVoiceActivity';
