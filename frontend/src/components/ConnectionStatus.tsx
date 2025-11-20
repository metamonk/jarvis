import React from 'react';

export type ConnectionStatusType = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface ConnectionStatusProps {
  status: ConnectionStatusType;
  errorMessage?: string;
}

const statusConfig = {
  connecting: {
    color: '#f59e0b',
    backgroundColor: '#fef3c7',
    text: 'Connecting...',
    ariaLabel: 'Connection status: connecting'
  },
  connected: {
    color: '#10b981',
    backgroundColor: '#d1fae5',
    text: 'Connected',
    ariaLabel: 'Connection status: connected'
  },
  disconnected: {
    color: '#ef4444',
    backgroundColor: '#fee2e2',
    text: 'Disconnected',
    ariaLabel: 'Connection status: disconnected'
  },
  error: {
    color: '#6b7280',
    backgroundColor: '#f3f4f6',
    text: 'Error',
    ariaLabel: 'Connection status: error'
  }
};

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ status, errorMessage }) => {
  const config = statusConfig[status];

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px 12px',
        borderRadius: '6px',
        backgroundColor: config.backgroundColor,
        fontSize: '14px',
        fontWeight: 500,
        color: config.color,
        transition: 'all 0.3s ease'
      }}
      role="status"
      aria-live="polite"
      aria-label={config.ariaLabel}
    >
      {/* Status indicator dot */}
      <span
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: config.color,
          display: 'inline-block',
          animation: status === 'connecting' ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
        }}
        aria-hidden="true"
      />

      {/* Status text */}
      <span>{config.text}</span>

      {/* Error message tooltip */}
      {errorMessage && (
        <div
          style={{
            position: 'relative',
            display: 'inline-block'
          }}
          title={errorMessage}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            style={{ cursor: 'help' }}
            aria-label={`Error: ${errorMessage}`}
          >
            <circle cx="8" cy="8" r="7" stroke={config.color} strokeWidth="2" fill="none" />
            <path
              d="M8 4V9M8 11V12"
              stroke={config.color}
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </div>
      )}

      <style>
        {`
          @keyframes pulse {
            0%, 100% {
              opacity: 1;
            }
            50% {
              opacity: 0.5;
            }
          }
        `}
      </style>
    </div>
  );
};

export default ConnectionStatus;
