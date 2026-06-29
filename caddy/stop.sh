#!/bin/bash

# FALO Go Redirection System - Stop Service Script
# Stops the Python admin UI and stops the Caddy process.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CADDY_DIR="$SCRIPT_DIR"

PID_FILE="$CADDY_DIR/admin_ui.pid"
CADDY_PID_FILE="$CADDY_DIR/caddy.pid"
CADDY_BIN="$CADDY_DIR/bin/caddy"

echo "----------------------------------------------------"
echo "🛑 正在停止 FALO Go 轉址管理平台與 Caddy 服務..."
echo "----------------------------------------------------"

# 1. 停止 Python 管理介面
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "📡 正在關閉 Python 管理介面 (PID: $PID)..."
        kill "$PID"
        sleep 1
    fi
    rm -f "$PID_FILE"
    echo "✅ Python 管理介面已停止。"
else
    echo "ℹ️ 未發現 Python 執行 PID，可能尚未啟動。"
fi

# 2. 停止 Caddy 服務
# 優先嘗試透過 Caddy Admin API 停止
if curl -s -X POST http://localhost:2019/stop > /dev/null 2>&1; then
    echo "✅ 成功透過 Admin API 停止 Caddy 服務。"
else
    # API 不通，嘗試使用 PID 檔案停止
    if [ -f "$CADDY_PID_FILE" ]; then
        CPID=$(cat "$CADDY_PID_FILE")
        if ps -p "$CPID" > /dev/null 2>&1; then
            echo "🛡️ 正在透過 PID 關閉 Caddy 進程 (PID: $CPID)..."
            kill "$CPID"
            sleep 1
        fi
        rm -f "$CADDY_PID_FILE"
        echo "✅ Caddy 進程已終止。"
    else
        # 備用方案: pkill
        if [ -f "$CADDY_BIN" ]; then
            pkill -f "$CADDY_BIN" > /dev/null 2>&1
            echo "✅ 已使用 pkill 清理 Caddy 殘留進程。"
        fi
    fi
fi

echo "----------------------------------------------------"
echo "🎉 服務已全部停止。"
echo "----------------------------------------------------"
