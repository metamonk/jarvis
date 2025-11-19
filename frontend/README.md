# Jarvis Frontend

Web client for the Jarvis voice assistant using React, TypeScript, and Vite.

## Technology Stack

- **Framework**: React 18.x
- **Language**: TypeScript 5.x
- **Build Tool**: Vite 5.x
- **Styling**: Tailwind CSS 3.x
- **Audio**: Web Audio API
- **WebSocket**: Native WebSocket API

## Features (MVP)

- Push-to-Talk (PTT) voice input
- WebSocket connection to backend
- Real-time audio streaming (WebRTC)
- Live transcript display
- Source attribution display
- Interruptibility support

## Setup

### Prerequisites

- Node.js 18+ (current version: 24.11.1)
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

### Running the Application

Development mode with hot module replacement:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Building for Production

```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/      # React components
│   ├── hooks/          # Custom React hooks
│   ├── services/       # WebSocket and API services
│   ├── types/          # TypeScript type definitions
│   ├── App.tsx         # Main application component
│   ├── main.tsx        # Application entry point
│   └── index.css       # Global styles (Tailwind)
├── public/             # Static assets
├── index.html          # HTML entry point
├── vite.config.ts      # Vite configuration
├── tsconfig.json       # TypeScript configuration
└── tailwind.config.js  # Tailwind CSS configuration
```

## Key Components to Implement

1. **VoiceInterface** - Main PTT button and audio visualization
2. **TranscriptDisplay** - Real-time display of user query and AI response
3. **WebSocketService** - Connection management and audio streaming
4. **AudioCapture** - Web Audio API integration for microphone access
5. **SourceAttribution** - Display sources for AI responses

## Environment Variables

Create a `.env` file:
```
VITE_WS_URL=ws://localhost:8000/ws
VITE_API_KEY=your_api_key_here
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Requires:
- WebSocket support
- Web Audio API
- MediaStream API (for microphone access)

## Development Notes

- The frontend communicates with the backend via WebSocket at `/ws` endpoint
- Audio is captured using Web Audio API and streamed as binary data
- Responses include both text transcript and audio playback
- All responses must display source attribution

## Troubleshooting

**Port conflicts**: Change the port in `vite.config.ts` if 5173 is in use

**WebSocket errors**: Verify backend is running and WebSocket URL is correct

**Microphone access**: Ensure HTTPS or localhost (HTTP) for microphone permissions

**Build errors**: Clear node_modules and reinstall: `rm -rf node_modules && npm install`
