#!/bin/bash

# FALO Go Redirection System - Start Service Script
# This starts the Python admin UI on port 8088. 
# Caddy is then automatically managed and spawned by the Python UI backend.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CADDY_DIR="$SCRIPT_DIR"

PID_FILE="$CADDY_DIR/admin_ui.pid"
LOG_FILE="$CADDY_DIR/admin_ui.log"

echo "----------------------------------------------------"
echo "🚀 正在啟動 FALO Go 轉址管理平台..."
echo "----------------------------------------------------"

# 1. 檢查 Python 3 狀態
if ! command -v python3 &> /dev/null; then
    echo "❌ 找不到 Python 3，請確認系統已安裝 Python"
    exit 1
fi

# 2. 檢查是否已經啟動
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️ Python 管理服務已經在執行中 (PID: $PID)"
        echo "💡 請使用 ./stop.sh 關閉後再重新啟動。"
        exit 0
    else
        echo "🧹 發現失效的 PID 檔案，清理中..."
        rm -f "$PID_FILE"
    fi
fi

# 3. 確保 Caddy 已經下載完成
CADDY_BIN="$CADDY_DIR/bin/caddy"
if [ ! -f "$CADDY_BIN" ]; then
    echo "🔍 找不到 Caddy 執行檔，正在執行下載腳本..."
    bash "$CADDY_DIR/scripts/setup-caddy.sh"
fi

# 4. 在背景啟動 Python 管理服務 (Flask)
echo "📡 正在背景啟動 Python 管理服務..."
nohup python3 -u "$CADDY_DIR/admin_ui/app.py" > "$LOG_FILE" 2>&1 &
PYTHON_PID=$!

# 將 PID 寫入檔案
echo "$PYTHON_PID" > "$PID_FILE"

# 稍等一下確認是否啟動成功
sleep 2

if ps -p "$PYTHON_PID" > /dev/null 2>&1; then
    echo "✅ 成功！Python 管理服務已啟動 (PID: $PYTHON_PID)"
    echo "🌐 管理網址 (go-admin): http://localhost:8088"
    echo "🌐 轉址網址 (go): http://localhost:8080"
    echo "📝 日誌儲存於: $LOG_FILE"
    echo "----------------------------------------------------"
else
    echo "❌ 啟動失敗！請檢查日誌: $LOG_FILE"
    exit 1
fi
