#!/usr/bin/env python3
import os
import urllib.request
import urllib.error
import json

class FaloCloudSDK:
    def __init__(self):
        # 載入本地 .env
        self.email = None
        self.api_key = None
        self.account_id = "4470c624a9068cf68a16c823a7aadf5a" # 從您的 Tunnel Token 解析出的 Account ID
        self._load_env()

    def _load_env(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        env_path = os.path.join(project_dir, '.env')
        
        env_vars = {}
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].strip().strip('"').strip("'")
                            env_vars[key] = val
                            
        self.email = env_vars.get("CLOUDFLARE_EMAIL")
        self.api_key = env_vars.get("CLOUDFLARE_API_KEY")

    def _request(self, method: str, path: str, data: dict = None) -> dict:
        url = f"https://api.cloudflare.com/client/v4{path}"
        req = urllib.request.Request(url, method=method)
        req.add_header("X-Auth-Email", self.email)
        req.add_header("X-Auth-Key", self.api_key)
        req.add_header("Content-Type", "application/json")
        
        body_bytes = None
        if data:
            body_bytes = json.dumps(data).encode('utf-8')
            
        try:
            with urllib.request.urlopen(req, data=body_bytes) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode('utf-8'))
                print(f"❌ API 錯誤: {err_body}")
                return err_body
            except:
                print(f"❌ HTTP 錯誤: {e.code} - {e.reason}")
                return {"success": False, "errors": [{"message": f"HTTP {e.code}"}]}

    def get_zone_id(self, domain_name: str = "formosa-ai.com") -> str:
        """獲取指定網域的 Zone ID"""
        res = self._request("GET", f"/zones?name={domain_name}")
        if res.get("success") and res.get("result"):
            return res["result"][0]["id"]
        return None

    def list_dns_records(self, zone_id: str) -> list:
        """列出指定 Zone 下的所有 DNS 記錄"""
        res = self._request("GET", f"/zones/{zone_id}/dns_records?per_page=100")
        if res.get("success"):
            return res.get("result", [])
        return []

    def create_or_update_dns_record(self, zone_id: str, subdomain: str, target: str, record_type: str = "CNAME", proxied: bool = True) -> dict:
        """建立或更新 DNS 記錄 (Agent-Friendly 自我修復式設計)"""
        fqdn = f"{subdomain}.formosa-ai.com" if subdomain else "formosa-ai.com"
        
        # 1. 檢查是否已存在
        records = self.list_dns_records(zone_id)
        existing_record = None
        for r in records:
            if r["name"] == fqdn:
                existing_record = r
                break
                
        payload = {
            "type": record_type,
            "name": fqdn,
            "content": target,
            "ttl": 1, # Automatic TTL
            "proxied": proxied
        }
        
        if existing_record:
            print(f"🔄 發現已存在的 DNS 記錄 ({fqdn})，正在更新中...")
            record_id = existing_record["id"]
            return self._request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", payload)
        else:
            print(f"➕ 正在建立新的 DNS 記錄 ({fqdn}) 指向 {target}...")
            return self._request("POST", f"/zones/{zone_id}/dns_records", payload)

    def list_tunnels(self) -> list:
        """列出此帳號下的所有 Tunnels"""
        res = self._request("GET", f"/accounts/{self.account_id}/tunnels")
        if res.get("success"):
            return res.get("result", [])
        return []

    def update_tunnel_configuration(self, tunnel_id: str, config: dict) -> dict:
        """更新指定 Tunnel 的遠端設定 (例如 Ingress Rules)"""
        path = f"/accounts/{self.account_id}/cfd_tunnel/{tunnel_id}/configurations"
        return self._request("PUT", path, {"config": config})

# 🚗 自我測試執行
if __name__ == "__main__":
    sdk = FaloCloudSDK()
    if not sdk.email or not sdk.api_key:
        print("❌ 未設定 Email 或 API Key，請檢查 .env 檔案")
        exit(1)
        
    print("--------------------------------------------------")
    print("🤖 FALO Cloud SDK 核心連線測試與基礎資料獲取")
    print("--------------------------------------------------")
    
    # 1. 獲取 Zone ID
    domain = "formosa-ai.com"
    print(f"🔍 正在獲取網域 {domain} 的 Zone ID...")
    zone_id = sdk.get_zone_id(domain)
    if zone_id:
        print(f"✅ 成功！Zone ID: {zone_id}")
    else:
        print(f"❌ 無法獲取 {domain} 的 Zone ID")
        exit(1)
        
    # 2. 列出 Tunnel
    print(f"\n🔍 正在讀取帳戶內的 Cloudflare Tunnels...")
    tunnels = sdk.list_tunnels()
    for t in tunnels:
        print(f"🛡️ Tunnel 名稱: {t['name']} | ID: {t['id']} | 狀態: {t['status']}")
        
    # 3. 列出現有的 DNS 記錄
    print(f"\n📖 正在讀取現有 DNS 記錄 (前 5 筆)...")
    records = sdk.list_dns_records(zone_id)
    for r in records[:5]:
        print(f"🌐 [{r['type']}] {r['name']} ──> {r['content']} (Proxied: {r['proxied']})")
    if len(records) > 5:
        print(f"... 以及其他 {len(records) - 5} 筆記錄")
    print("--------------------------------------------------")
