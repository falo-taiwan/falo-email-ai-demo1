#!/bin/bash

# FALO Edge Platform: cloudflared Tunnel Execution Script
# Reads token from .env and starts the tunnel locally.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"
CLOUDFLARED_BIN="$PROJECT_DIR/bin/cloudflared"

# 1. Check for cloudflared binary
if [ ! -f "$CLOUDFLARED_BIN" ]; then
    echo "❌ Local cloudflared binary not found at $CLOUDFLARED_BIN"
    echo "💡 Please run './scripts/setup.sh' first to download and prepare the binary."
    exit 1
fi

# 2. Check for .env file
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file (.env) not found at $ENV_FILE"
    echo "💡 Please copy .env.example to .env and configure your CLOUDFLARE_TUNNEL_TOKEN:"
    echo "   cp .env.example .env"
    exit 1
fi

# Load variables from .env
# Using a clean export strategy that ignores comments and empty lines
export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)

# 3. Check for CLOUDFLARE_TUNNEL_TOKEN
if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
    echo "❌ CLOUDFLARE_TUNNEL_TOKEN is not defined in your .env file."
    echo "💡 Please check the content of $ENV_FILE and insert your token."
    exit 1
fi

echo "🚀 Starting Cloudflare Tunnel (falo-dev-tunnel)..."
echo "Press Ctrl+C to stop the agent."
echo "---------------------------------------------------------"

exec "$CLOUDFLARED_BIN" tunnel run --token "$CLOUDFLARE_TUNNEL_TOKEN"
