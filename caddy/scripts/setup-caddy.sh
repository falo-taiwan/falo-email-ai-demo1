#!/bin/bash
set -e

# FALO Caddy Setup Script
# Detects system architecture, downloads Caddy binary, and verifies installation locally.

echo "🔍 偵測系統架構中..."
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

if [ "$OS" != "darwin" ]; then
    echo "⚠️ 此腳本專為 macOS 優化。當前系統為 $OS。"
    echo "請至 Caddy 官網下載適用您系統的執行檔：https://caddyserver.com/download"
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
        echo "❌ 不支援的 macOS 架構: $ARCH"
        exit 1
        ;;
esac

echo "✅ 系統偵測結果: macOS ($ARCH)"

# 取得腳本所在的目錄與專案目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CADDY_DIR="$(dirname "$SCRIPT_DIR")"
BIN_DIR="$CADDY_DIR/bin"

# 建立 bin 目錄
mkdir -p "$BIN_DIR"

DOWNLOAD_URL="https://caddyserver.com/api/download?os=darwin&arch=${DOWNLOAD_ARCH}"
CADDY_BIN="$BIN_DIR/caddy"

echo "📥 正在從 Caddy 官網下載執行檔..."
echo "下載連結: $DOWNLOAD_URL"

# 下載 Caddy (使用 -L 跟隨重定向)
curl -L -o "$CADDY_BIN" "$DOWNLOAD_URL"

echo "🔒 設定執行權限..."
chmod +x "$CADDY_BIN"

echo "🔬 驗證 Caddy 安裝狀態..."
VER="$("$CADDY_BIN" version)"
echo "🎉 Caddy 安裝成功！"
echo "版本資訊: $VER"
