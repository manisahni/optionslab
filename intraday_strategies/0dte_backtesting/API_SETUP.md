# API Setup Guide

This guide will help you set up and configure the API connections required for the 0DTE Trading Application.

## Quick Start

```bash
# 1. Run the setup wizard
./setup_api_keys.py

# 2. Validate connections
./validate_connections.py

# 3. Start the application
python start.py
```

## Required APIs

### OpenAI API (Required)
- Powers AI trading analysis
- Get your key at: https://platform.openai.com/api-keys

### Interactive Brokers (Optional)
- For downloading market data
- Only needed if updating SPY data

## Manual Setup

1. Copy the example file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your keys:
```
OPENAI_API_KEY=your-api-key-here
```

## Troubleshooting

Run with `--fix` flag for help:
```bash
./validate_connections.py --fix
```

## Security Notes

- Never commit your `.env` file
- API keys are automatically masked in logs
- Keys are stored locally only

For detailed setup instructions, see the full documentation.