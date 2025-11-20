import React, { useEffect, useCallback, useRef } from 'react';

interface PushToTalkButtonProps {
  onPressStart: () => void;
  onPressEnd: () => void;
  isRecording: boolean;
  isProcessing: boolean;
  disabled?: boolean;
}

const PushToTalkButton: React.FC<PushToTalkButtonProps> = ({
  onPressStart,
  onPressEnd,
  isRecording,
  isProcessing,
  disabled = false,
}) => {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const isSpaceKeyDownRef = useRef(false);

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Only respond to Space key
      if (event.code !== 'Space') return;

      // Prevent default space bar behavior (scrolling)
      event.preventDefault();

      // Ignore if disabled
      if (disabled) return;

      // Ignore repeated keydown events when key is held
      if (isSpaceKeyDownRef.current) return;

      isSpaceKeyDownRef.current = true;
      onPressStart();
    },
    [onPressStart, disabled]
  );

  const handleKeyUp = useCallback(
    (event: KeyboardEvent) => {
      if (event.code !== 'Space') return;

      event.preventDefault();

      // Ignore if disabled
      if (disabled) return;

      if (isSpaceKeyDownRef.current) {
        isSpaceKeyDownRef.current = false;
        onPressEnd();
      }
    },
    [onPressEnd, disabled]
  );

  // Set up global keyboard listeners
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [handleKeyDown, handleKeyUp]);

  // Handle mouse/touch events
  const handlePointerDown = (event: React.PointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    if (disabled) return;
    onPressStart();
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    if (disabled) return;
    onPressEnd();
  };

  const handlePointerLeave = (event: React.PointerEvent<HTMLButtonElement>) => {
    // If pointer leaves while pressed, treat as release
    if (disabled) return;
    if (event.buttons === 1) {
      onPressEnd();
    }
  };

  // Determine visual state
  const getButtonState = () => {
    if (disabled) return 'disabled';
    if (isProcessing) return 'processing';
    if (isRecording) return 'recording';
    return 'idle';
  };

  const buttonState = getButtonState();

  // Get button text based on state
  const getButtonText = () => {
    switch (buttonState) {
      case 'disabled':
        return 'Connect First';
      case 'recording':
        return 'Recording...';
      case 'processing':
        return 'Processing...';
      default:
        return 'Push to Talk';
    }
  };

  // Get ARIA label based on state
  const getAriaLabel = () => {
    switch (buttonState) {
      case 'disabled':
        return 'Button disabled. Please connect to the server first.';
      case 'recording':
        return 'Recording in progress. Release to stop.';
      case 'processing':
        return 'Processing your request. Please wait.';
      default:
        return 'Press and hold Space bar or click and hold to talk';
    }
  };

  // Get tooltip title based on state
  const getTitle = () => {
    if (disabled) {
      return 'Connect to server first';
    }
    return 'Press and hold Space or click to talk';
  };

  return (
    <button
      ref={buttonRef}
      className={`push-to-talk-button push-to-talk-button--${buttonState}`}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerLeave}
      disabled={isProcessing || disabled}
      aria-label={getAriaLabel()}
      aria-pressed={isRecording}
      title={getTitle()}
      type="button"
      style={styles.button}
    >
      <div
        className="push-to-talk-button__pulse"
        style={{
          ...styles.pulse,
          ...(isRecording ? styles.pulseActive : {}),
        }}
      />
      <div
        className="push-to-talk-button__icon"
        style={{
          ...styles.icon,
          ...(buttonState === 'disabled' && styles.iconDisabled),
          ...(buttonState === 'recording' && styles.iconRecording),
          ...(buttonState === 'processing' && styles.iconProcessing),
        }}
      >
        {(buttonState === 'idle' || buttonState === 'disabled') && (
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
            {buttonState === 'disabled' && (
              <line x1="4" y1="4" x2="20" y2="20" strokeWidth="3" />
            )}
          </svg>
        )}
        {buttonState === 'recording' && (
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <circle cx="12" cy="12" r="8" />
          </svg>
        )}
        {buttonState === 'processing' && (
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={styles.spinner}
          >
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
        )}
      </div>
      <div className="push-to-talk-button__text" style={styles.text}>
        {getButtonText()}
      </div>
    </button>
  );
};

// Inline styles
const styles: { [key: string]: React.CSSProperties } = {
  button: {
    position: 'relative',
    width: '200px',
    height: '200px',
    borderRadius: '50%',
    border: '4px solid #e0e0e0',
    backgroundColor: '#ffffff',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    transition: 'all 0.2s ease',
    outline: 'none',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08)',
    userSelect: 'none',
    WebkitTapHighlightColor: 'transparent',
  },
  pulse: {
    position: 'absolute',
    top: '-4px',
    left: '-4px',
    right: '-4px',
    bottom: '-4px',
    borderRadius: '50%',
    border: '4px solid #4CAF50',
    opacity: 0,
    transform: 'scale(1)',
    transition: 'all 0.3s ease',
    pointerEvents: 'none',
  },
  pulseActive: {
    opacity: 1,
    animation: 'pulse 1.5s ease-in-out infinite',
  },
  icon: {
    color: '#666',
    transition: 'all 0.3s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconDisabled: {
    color: '#bdbdbd',
  },
  iconRecording: {
    color: '#f44336',
  },
  iconProcessing: {
    color: '#2196F3',
  },
  text: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#333',
    textAlign: 'center',
    transition: 'color 0.3s ease',
  },
  spinner: {
    animation: 'spin 1s linear infinite',
  },
};

// Add global styles for animations
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes pulse {
    0% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.1);
      opacity: 0.5;
    }
    100% {
      transform: scale(1);
      opacity: 1;
    }
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .push-to-talk-button:hover:not(:disabled) {
    transform: scale(1.05);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15), 0 2px 4px rgba(0, 0, 0, 0.12);
    border-color: #4CAF50;
  }

  .push-to-talk-button:active:not(:disabled) {
    transform: scale(0.95);
  }

  .push-to-talk-button--recording {
    border-color: #f44336;
    background-color: #ffebee;
  }

  .push-to-talk-button--processing {
    border-color: #2196F3;
    background-color: #e3f2fd;
    cursor: not-allowed;
    opacity: 0.8;
  }

  .push-to-talk-button--disabled {
    border-color: #e0e0e0;
    background-color: #fafafa;
    cursor: not-allowed;
    opacity: 0.5;
  }

  .push-to-talk-button--disabled .push-to-talk-button__text {
    color: #9e9e9e;
  }

  .push-to-talk-button:disabled {
    cursor: not-allowed;
    opacity: 0.5;
    transform: scale(1) !important;
  }

  .push-to-talk-button:disabled:hover {
    transform: scale(1) !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    border-color: #e0e0e0 !important;
  }

  .push-to-talk-button:focus-visible {
    outline: 3px solid #4CAF50;
    outline-offset: 4px;
  }
`;

if (typeof document !== 'undefined') {
  document.head.appendChild(styleSheet);
}

export default PushToTalkButton;
