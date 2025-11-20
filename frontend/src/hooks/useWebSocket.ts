import { useEffect, useRef, useState, useCallback } from 'react';

// Connection state constants and type
export const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error',
} as const;

export type ConnectionState = typeof ConnectionState[keyof typeof ConnectionState];

export interface WebSocketConfig {
  url: string;
  protocols?: string | string[];
  reconnectAttempts?: number;
  reconnectInterval?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (data: ArrayBuffer) => void;
}

export interface UseWebSocketReturn {
  connectionState: ConnectionState;
  sendMessage: (data: ArrayBuffer | Blob | string) => void;
  connect: () => void;
  disconnect: () => void;
  isConnected: boolean;
}

// Type aliases for compatibility with hooks/index.ts
export type WebSocketState = ConnectionState;
export type UseWebSocketOptions = WebSocketConfig;

/**
 * Custom hook for managing WebSocket connections with automatic reconnection
 * and binary message support.
 *
 * Features:
 * - Automatic reconnection with configurable retry attempts
 * - Connection state tracking
 * - Binary message support (ArrayBuffer)
 * - Clean connection lifecycle management
 * - Type-safe implementation
 *
 * @param config - WebSocket configuration options
 * @returns WebSocket connection state and control methods
 */
export const useWebSocket = (config: WebSocketConfig): UseWebSocketReturn => {
  const {
    url,
    protocols,
    reconnectAttempts = 3,
    reconnectInterval = 3000,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = config;

  const [connectionState, setConnectionState] = useState<ConnectionState>(
    ConnectionState.DISCONNECTED
  );

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const shouldReconnectRef = useRef<boolean>(true);
  const isManualDisconnectRef = useRef<boolean>(false);

  /**
   * Clear any pending reconnection timeout
   */
  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  /**
   * Attempt to reconnect to the WebSocket server
   */
  const attemptReconnect = useCallback(() => {
    if (!shouldReconnectRef.current || isManualDisconnectRef.current) {
      return;
    }

    if (reconnectAttemptsRef.current < reconnectAttempts) {
      reconnectAttemptsRef.current += 1;
      console.log(
        `Attempting to reconnect (${reconnectAttemptsRef.current}/${reconnectAttempts})...`
      );

      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, reconnectInterval) as number;
    } else {
      console.error('Max reconnection attempts reached');
      setConnectionState(ConnectionState.ERROR);
    }
  }, [reconnectAttempts, reconnectInterval]);

  /**
   * Connect to the WebSocket server
   */
  const connect = useCallback(() => {
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      setConnectionState(ConnectionState.CONNECTING);
      isManualDisconnectRef.current = false;

      const ws = new WebSocket(url, protocols);
      ws.binaryType = 'arraybuffer'; // Set binary type for audio data

      ws.onopen = (event: Event) => {
        console.log('WebSocket connected');
        setConnectionState(ConnectionState.CONNECTED);
        reconnectAttemptsRef.current = 0; // Reset reconnect attempts on successful connection
        clearReconnectTimeout();

        if (onOpen) {
          onOpen(event);
        }
      };

      ws.onclose = (event: CloseEvent) => {
        console.log('WebSocket closed', event.code, event.reason);
        wsRef.current = null;

        if (!isManualDisconnectRef.current) {
          setConnectionState(ConnectionState.DISCONNECTED);
          attemptReconnect();
        } else {
          setConnectionState(ConnectionState.DISCONNECTED);
        }

        if (onClose) {
          onClose(event);
        }
      };

      ws.onerror = (event: Event) => {
        console.error('WebSocket error', event);
        setConnectionState(ConnectionState.ERROR);

        if (onError) {
          onError(event);
        }
      };

      ws.onmessage = (event: MessageEvent) => {
        if (onMessage && event.data instanceof ArrayBuffer) {
          onMessage(event.data);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionState(ConnectionState.ERROR);
      attemptReconnect();
    }
  }, [url, protocols, onOpen, onClose, onError, onMessage, clearReconnectTimeout, attemptReconnect]);

  /**
   * Disconnect from the WebSocket server
   */
  const disconnect = useCallback(() => {
    console.log('Manually disconnecting WebSocket');
    isManualDisconnectRef.current = true;
    shouldReconnectRef.current = false;
    clearReconnectTimeout();

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnecting');
      wsRef.current = null;
    }

    setConnectionState(ConnectionState.DISCONNECTED);
  }, [clearReconnectTimeout]);

  /**
   * Send a message through the WebSocket connection
   */
  const sendMessage = useCallback((data: ArrayBuffer | Blob | string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    } else {
      console.warn('WebSocket is not connected. Message not sent.');
    }
  }, []);

  /**
   * Initialize connection on mount
   */
  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    // Cleanup on unmount
    return () => {
      shouldReconnectRef.current = false;
      clearReconnectTimeout();

      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
        wsRef.current = null;
      }
    };
  }, [url, protocols]); // Only reconnect if URL or protocols change

  const isConnected = connectionState === ConnectionState.CONNECTED;

  return {
    connectionState,
    sendMessage,
    connect,
    disconnect,
    isConnected,
  };
};
