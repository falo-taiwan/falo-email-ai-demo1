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
    domain = "formosa-ai.com"
    
    if not sdk.email or not sdk.api_key:
        print("❌ 未設定 Email 或 API Key，請檢查 .env 檔案")
        return
        
    print("--------------------------------------------------")
    print("🌐 FALO Cloud DNS 註冊程序 - 串接 Cloudflare")
    print("--------------------------------------------------")
    
    print("🔍 正在獲取網域 Zone ID...")
    zone_id = sdk.get_zone_id(domain)
    if not zone_id:
        print("❌ 無法獲取 Zone ID")
        return
    print(f"✅ 成功獲取 Zone ID: {zone_id}")
    
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
    
    cname_target = f"{tunnel_id}.cfargotunnel.com"
    print(f"✅ 找到 Tunnel ID: {tunnel_id}")
    print(f"🔗 Tunnel CNAME 目標: {cname_target}")
    
    # 1. 建立/更新 go.formosa-ai.com
    print("\n➕ 正在建立/更新 CNAME 記錄: go.formosa-ai.com ──► Tunnel")
    res_go = sdk.create_or_update_dns_record(zone_id, "go", cname_target, "CNAME", True)
    if res_go.get("success"):
        print("✅ go.formosa-ai.com DNS 記錄設定/更新成功！")
    else:
        print(f"❌ go.formosa-ai.com 設定失敗: {res_go}")
        
    # 2. 建立/更新 go-admin.formosa-ai.com
    print("\n➕ 正在建立/更新 CNAME 記錄: go-admin.formosa-ai.com ──► Tunnel")
    res_admin = sdk.create_or_update_dns_record(zone_id, "go-admin", cname_target, "CNAME", True)
    if res_admin.get("success"):
        print("✅ go-admin.formosa-ai.com DNS 記錄設定/更新成功！")
    else:
        print(f"❌ go-admin.formosa-ai.com 設定失敗: {res_admin}")
        
    print("--------------------------------------------------")
    print("🎉 DNS 推送完成！")
    print("💡 請注意：您仍需在 Cloudflare Zero Trust 後台的 Public Hostname 設定中，")
    print("   將 go.formosa-ai.com 指向 http://localhost:8080 (Caddy)")
    print("   將 go-admin.formosa-ai.com 指向 http://localhost:8088 (Python Admin)")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()
