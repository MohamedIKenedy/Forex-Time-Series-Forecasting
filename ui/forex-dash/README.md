# Forex Terminal Dashboard

A terminal-style dashboard for monitoring and controlling forex data streaming with a command-line interface.

## Features

- **Terminal Interface**: Access all functionality via command-line commands
- **Live Streaming**: Start/stop streaming of forex ticker data
- **Status Monitoring**: Check current streaming status
- **Dark Theme**: GitHub-inspired dark terminal UI
- **Real-time Updates**: Built with React and TypeScript

## Available Commands

```
start [ticker]      - Start streaming data (optionally for specific ticker)
stop                - Stop streaming
status              - Show streaming status
plot [ticker]       - Display plot for a specific ticker
help                - Show available commands
clear               - Clear terminal output
```

## Getting Started

### Prerequisites
- Node.js 20.19+ or 22.12+
- Running FastAPI backend (api/main.py) on localhost:8000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The dashboard will be available at `http://localhost:5174` (or next available port)

### Environment Setup

Ensure your FastAPI backend is running with CORS enabled:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify ["http://localhost:5174"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Usage Examples

```
# Start streaming all tickers
> start

# Check streaming status
> status

# Stop streaming
> stop

# Display a plot for a specific ticker
> plot EURUSD=X

# Show all available commands
> help

# Clear terminal
> clear
```

## Project Structure

- `src/components/Terminal.tsx` - Main terminal UI component
- `src/components/PlotDisplay.tsx` - Plot display component
- `src/commandHandler.ts` - Command parsing and execution logic
- `src/api.ts` - API client for FastAPI backend
- `src/types.ts` - TypeScript type definitions

## Building for Production

```bash
npm run build
```

## Configuration

To change the API endpoint, edit `src/api.ts`:

```typescript
const API_BASE_URL = 'http://localhost:8000';
```

## Supported Tickers

- EURUSD=X
- GBPUSD=X
- USDJPY=X
- USDCHF=X
- USDCAD=X
- AUDUSD=X
- NZDUSD=X
- EURMAD=X
- EURRUB=X
- RUBUSD=X
