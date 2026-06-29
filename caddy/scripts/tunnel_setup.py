#!/usr/bin/env python3
import sys
import os

# 確保能 import 專案 scripts 目錄下的 falo_cloud_sdk
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.append(os.path.join(PROJECT_DIR, "scripts"))

from falo_cloud_sdk import FaloCloudSDK

def main():
    sdk = FaloCloudSDK()
    
    if not sdk.email or not sdk.api_key:
        print("❌ 未設定 Email 或 API Key，請檢查 .env 檔案")
        return
        
    print("--------------------------------------------------")
    print("🛡️ FALO Cloud Tunnel Ingress 配置程序 - 串接 Cloudflare")
    print("--------------------------------------------------")
    
    # 尋找 falo-dev-tunnel
    print("🔍 正在尋找 falo-dev-tunnel...")
    tunnels = sdk.list_tunnels()
    tunnel_id = None
    for t in tunnels:
        if t["name"] == "falo-dev-tunnel":
            tunnel_id = t["id"]
            break
            
    if not tunnel_id:
        print("❌ 找不到 falo-dev-tunnel，請確認 Tunnel 是否已存在。")
        return
    
    print(f"✅ 找到 Tunnel ID: {tunnel_id}")
    
    # 構築 Ingress Rules 設定
    ingress_config = {
        "ingress": [
            {
                "hostname": "go-admin.formosa-ai.com",
                "service": "http://localhost:8088"
            },
            {
                "hostname": "go.formosa-ai.com",
                "service": "http://localhost:8080"
            },
            {
                "hostname": "dev.formosa-ai.com",
                "service": "http://localhost:8080"
            },
            {
                "service": "http_status:404"
            }
        ]
    }
    
    print("⚙️ 正在向 Cloudflare API 寫入 Ingress Rules...")
    res = sdk.update_tunnel_configuration(tunnel_id, ingress_config)
    
    if res.get("success"):
        print("🎉 Cloudflare Tunnel Ingress 路由規則寫入成功！")
        print("--------------------------------------------------")
        print("🔗 綁定規則：")
        print("  1. go-admin.formosa-ai.com ──► http://localhost:8088 (Python Admin)")
        print("  2. go.formosa-ai.com       ──► http://localhost:8080 (Caddy Gateway)")
        print("  3. dev.formosa-ai.com      ──► http://localhost:8080 (Caddy Gateway)")
        print("  4. 其它未匹配網址           ──► HTTP 404")
        print("--------------------------------------------------")
        print("💡 請等待 5~10 秒讓 cloudflared 連線同步設定，即可直接透過網址訪問。")
    else:
        print(f"❌ 寫入失敗: {res}")
        print("💡 請確認您的 API Key 是否具備 Cloudflare Tunnel (or One Connectors) 的 Write 權限。")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()
