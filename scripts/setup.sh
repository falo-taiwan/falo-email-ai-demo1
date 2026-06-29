#!/bin/bash
set -e

# FALO Edge Platform: cloudflared Setup Script
# Detects OS and architecture, downloads cloudflared, and verifies installation locally.

echo "🔍 Detecting system architecture..."
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

if [ "$OS" != "darwin" ]; then
    echo "⚠️ This setup script is optimized for macOS. Current OS is $OS."
    echo "Please download the appropriate binary manually from https://github.com/cloudflare/cloudflared/releases"
    exit 1
fi

case "$ARCH" in
    x86_64)
        DOWNLOAD_ARCH="amd64"
        ;;
    arm64)
        DOWNLOAD_ARCH="arm64"
        ;;
    *)
        echo "❌ Unsupported macOS architecture: $ARCH"
        exit 1
        ;;
esac

echo "✅ System: macOS ($ARCH)"

# Create bin directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BIN_DIR="$PROJECT_DIR/bin"
mkdir -p "$BIN_DIR"

DOWNLOAD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-${DOWNLOAD_ARCH}.tgz"
TEMP_TAR="$BIN_DIR/cloudflared.tgz"

echo "📥 Downloading cloudflared binary from: $DOWNLOAD_URL"
curl -L -o "$TEMP_TAR" "$DOWNLOAD_URL"

echo "📦 Extracting package..."
tar -xzf "$TEMP_TAR" -C "$BIN_DIR"

echo "🧹 Cleaning up temporary archives..."
rm -f "$TEMP_TAR"

echo "🔒 Setting executable permissions..."
chmod +x "$BIN_DIR/cloudflared"

echo "🔬 Verifying cloudflared installation..."
VER="$("$BIN_DIR/cloudflared" --version)"
echo "🎉 cloudflared successfully installed!"
echo "Version Info: $VER"
