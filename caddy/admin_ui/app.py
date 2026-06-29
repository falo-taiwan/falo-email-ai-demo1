#!/usr/bin/env python3
import os
import sys
import csv
import io
import json
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, Response, make_response

# 確保能 import 同目錄下的 caddy_manager 與 tunnel_manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from caddy_manager import CaddyManager
from tunnel_manager import TunnelProcessManager

app = Flask(__name__)

# 取得專案根目錄下的 caddy 資料夾路徑
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CADDY_DIR = os.path.dirname(SCRIPT_DIR)

manager = CaddyManager(CADDY_DIR)
tunnel_manager = TunnelProcessManager(CADDY_DIR)

# 在系統載入時，預設自動將 Caddy 與相關設定檔初始化，並啟動 Caddy 和 Tunnel Agent
def initialize_system():
    # 預先載入 rules.json 並自動套用最新 Caddyfile
    rules = manager.load_rules()
    caddyfile_content = manager.generate_caddyfile_content(rules)
    with open(manager.caddyfile_path, "w", encoding="utf-8") as f:
        f.write(caddyfile_content)

    print("🚀 正在初始化 Caddy 轉址服務與 Caddyfile...")
    res_caddy = manager.start_with_pidfile()
    print(f"📡 Caddy 啟動結果: {res_caddy['message']}")

    print("🚀 正在初始化 Cloudflare Tunnel 服務...")
    res_tunnel = tunnel_manager.start()
    print(f"📡 Cloudflare Tunnel 啟動結果: {res_tunnel['message']}")

initialize_system()

# 密碼保護 (HTTP Basic Auth) - 確保對外公網訪問時的安全
@app.before_request
def check_authentication():
    auth = request.authorization
    if not auth or auth.username != 'falo' or auth.password != 'force':
        return Response(
            '🔐 Unauthorized access. Please log in with correct credentials.', 401,
            {'WWW-Authenticate': 'Basic realm="FALO Go Admin Login Required"'}
        )

@app.route("/")
def index():
    # 這裡使用單一檔案的 HTML (Inlined Template)，方便統一管理，也符合 Agent-Friendly 單一 HTML 部署思維
    # 讀取 templates/index.html，如果沒有就使用預設的 fallback 模板字串
    template_path = os.path.join(SCRIPT_DIR, "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    else:
        html_content = "<h1>Index template not found. Please create template first.</h1>"
    return render_template_string(html_content)

@app.route("/api/status", methods=["GET"])
def get_status():
    status_info = manager.get_status()
    # 同時回傳目前的規則數量
    rules = manager.load_rules()
    status_info["rules_count"] = len(rules)
    return jsonify(status_info)

@app.route("/api/start", methods=["POST"])
def start_caddy():
    res = manager.start_with_pidfile()
    return jsonify(res)

@app.route("/api/stop", methods=["POST"])
def stop_caddy():
    res = manager.stop()
    return jsonify(res)

@app.route("/api/rules", methods=["GET", "POST"])
def manage_rules():
    if request.method == "POST":
        rules = request.json
        if not isinstance(rules, list):
            return jsonify({"success": False, "message": "無效的規則格式，必須為列表"})
        res = manager.save_rules_and_reload(rules)
        return jsonify(res)
    else:
        rules = manager.load_rules()
        return jsonify(rules)

@app.route("/api/logs", methods=["GET"])
def get_logs():
    log_file = os.path.join(CADDY_DIR, "caddy.log")
    if not os.path.exists(log_file):
        return jsonify({"logs": "目前尚無日誌記錄 (Caddy 可能尚未啟動過或尚未寫入日誌)"})
    try:
        # 讀取最後 100 行日誌
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            last_lines = lines[-100:]
            return jsonify({"logs": "".join(last_lines)})
    except Exception as e:
        return jsonify({"logs": f"無法讀取日誌: {str(e)}"})

# --- Cloudflare Tunnel 相關 API ---
@app.route("/api/tunnel/status", methods=["GET"])
def get_tunnel_status():
    status_info = tunnel_manager.get_status()
    return jsonify(status_info)

@app.route("/api/tunnel/start", methods=["POST"])
def start_tunnel():
    res = tunnel_manager.start()
    return jsonify(res)

@app.route("/api/tunnel/stop", methods=["POST"])
def stop_tunnel():
    res = tunnel_manager.stop()
    return jsonify(res)

@app.route("/api/tunnel/logs", methods=["GET"])
def get_tunnel_logs():
    log_file = os.path.join(CADDY_DIR, "cloudflared.log")
    if not os.path.exists(log_file):
        return jsonify({"logs": "目前尚無日誌記錄 (cloudflared 可能尚未啟動過)"})
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            last_lines = lines[-100:]
            return jsonify({"logs": "".join(last_lines)})
    except Exception as e:
        return jsonify({"logs": f"無法讀取日誌: {str(e)}"})

# --- 轉址連線訪問紀錄相關 API ---
def get_visit_history(log_file_path: str) -> list:
    if not os.path.exists(log_file_path):
        return []
    
    visits = []
    try:
        with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # 只處理 Caddy access log
                    logger_name = data.get("logger", "")
                    if not logger_name or not logger_name.startswith("http.log.access"):
                        continue
                    
                    req = data.get("request", {})
                    uri = req.get("uri", "")
                    
                    # 隱藏健康檢查以防洗板
                    if uri == "/caddy-health":
                        continue
                        
                    ts = data.get("ts", 0)
                    dt_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "-"
                    
                    resp_headers = data.get("resp_headers", {})
                    location = resp_headers.get("Location", [""])[0] if "Location" in resp_headers else ""
                    
                    visits.append({
                        "timestamp": dt_str,
                        "client_ip": req.get("remote_ip", "-"),
                        "host": req.get("host", "-"),
                        "path": uri,
                        "method": req.get("method", "-"),
                        "status": data.get("status", 0),
                        "redirect_target": location
                    })
                except Exception:
                    pass
    except Exception:
        pass
        
    visits.reverse()  # 最新時間排最前面
    return visits

@app.route("/api/visits", methods=["GET"])
def get_visits():
    log_file = os.path.join(CADDY_DIR, "caddy.log")
    visits = get_visit_history(log_file)
    return jsonify(visits)

@app.route("/api/visits/clear", methods=["POST"])
def clear_visits():
    log_file = os.path.join(CADDY_DIR, "caddy.log")
    try:
        # 清空日誌檔案
        if os.path.exists(log_file):
            open(log_file, "w").close()
        return jsonify({"success": True, "message": "連線訪問紀錄已成功清除"})
    except Exception as e:
        return jsonify({"success": False, "message": f"清除失敗: {str(e)}"})

@app.route("/api/visits/export", methods=["GET"])
def export_visits():
    log_file = os.path.join(CADDY_DIR, "caddy.log")
    visits = get_visit_history(log_file)
    
    si = io.StringIO()
    cw = csv.writer(si)
    # 寫入 CSV 標頭
    cw.writerow(["訪問時間", "來源 IP", "主機名稱", "路徑", "請求方法", "響應狀態", "轉址目標"])
    
    # 寫入數據
    for v in visits:
        cw.writerow([
            v["timestamp"],
            v["client_ip"],
            v["host"],
            v["path"],
            v["method"],
            v["status"],
            v["redirect_target"]
        ])
        
    # 回傳 CSV Response (加上 UTF-8-SIG BOM 讓 Excel 點開能正確顯示中文不亂碼)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=falo_go_visits.csv"
    output.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return output

if __name__ == "__main__":
    print("🔥 啟動 FALO Caddy 管理伺服器...")
    # 執行 Flask 伺服器，監聽 8088 port
    # 使用 threaded=True 確保多執行緒處理，避免阻礙 Caddy 的相關 API 連線
    app.run(host="0.0.0.0", port=8088, debug=False)
