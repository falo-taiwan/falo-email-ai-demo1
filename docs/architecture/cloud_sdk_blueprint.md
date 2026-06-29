# Module 2: Cloud SDK Blueprint (FALO Cloud SDK Python 規格書)

本模組定義了 **FALO Cloud SDK (`falo-cloud-sdk`)** 的架構與 Python API 介面規格。SDK 的核心理念是 **Agent-Friendly**，即所有的 API 回傳結構皆為強型別或清晰定義的 JSON Schema，以便 AI 代理人可以直接解析並自我決定下一步行動。

---

## 🏛️ SDK 元件架構圖 (Component Map)

FALO Cloud SDK 採用層次化架構，使 Agent 能夠透過統一的 `FaloCloudManager` 入口操作所有邊緣層資源：

```
                    ┌─────────────────────────┐
                    │     AI Agent (Python)   │
                    └────────────┬────────────┘
                                 │ (呼叫 API)
                                 ▼
                    ┌─────────────────────────┐
                    │    FaloCloudManager     │
                    └────────────┬────────────┘
                                 │
         ┌───────────────┬───────┴───────┬───────────────┐
         ▼               ▼               ▼               ▼
   [ DNSManager ] [ TunnelManager ] [ R2Manager ] [ WorkerManager ]
         │               │               │               │
         └───────────────┼───────────────┼───────────────┘
                         ▼
         ┌─────────────────────────┐
         │   Cloudflare API Core   │
         │   (Requests / HTTP2)    │
         └─────────────────────────┘
```

---

## 🐍 SDK API Interface 宣告 (Python Spec)

### 1. 核心管理器 (FaloCloudManager)
```python
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class SDKConfig:
    cloudflare_api_token: str
    account_id: str
    zone_id: str
    environment: str = "development" # development | production

class FaloCloudManager:
    def __init__(self, config: SDKConfig):
        self.config = config
        self.dns = DNSManager(config)
        self.tunnel = TunnelManager(config)
        self.r2 = R2Manager(config)
        self.workers = WorkerManager(config)
```

---

### 2. DNS 模組 (DNSManager)
```python
class DNSManager:
    def create_dns(self, subdomain: str, target: str, proxied: bool = True) -> Dict[str, Any]:
        """
        在 Cloudflare 建立或更新 DNS 記錄。
        
        Args:
            subdomain: 子網域名稱 (例如 "api")
            target: 指向的目標 (例如 Tunnel 的 CNAME 地址)
            proxied: 是否啟用 Cloudflare Proxy 橘色雲朵 (CDN/WAF 防護)
            
        Returns:
            符合 Agent-friendly 結構的字典，例如:
            {
                "status": "success",
                "dns_id": "dns_rec_abc123",
                "fqdn": "api.formosa-ai.com",
                "target": "69b19190-6dff-4156-a192-2409871ecab9.cfargotunnel.com",
                "proxied": True
            }
        """
        pass
```

---

### 3. Tunnel 模組 (TunnelManager)
```python
class TunnelManager:
    def create_tunnel(self, name: str) -> Dict[str, Any]:
        """
        在 Cloudflare 端建立一個新的 Tunnel。
        
        Returns:
            {
                "status": "created",
                "tunnel_id": "69b19190-6dff-4156-a192-2409871ecab9",
                "tunnel_name": "falo-dev-tunnel",
                "token": "eyJhIjoiNDQ3MGM...",  # 用於本機部署的關鍵 Token
                "connector_status": "inactive"
            }
        """
        pass

    def create_hostname(self, tunnel_id: str, subdomain: str, service_url: str) -> Dict[str, Any]:
        """
        將特定的 Subdomain 路由對接到本機 Port。
        
        Args:
            tunnel_id: 建立的 Tunnel ID
            subdomain: 欲對外的子域名 (如 "dev")
            service_url: 本機目標埠口 (如 "http://localhost:8080")
            
        Returns:
            {
                "status": "mapped",
                "hostname": "dev.formosa-ai.com",
                "service": "http://localhost:8080",
                "cname_target": "69b19190-6dff-4156-a192-2409871ecab9.cfargotunnel.com"
            }
        """
        pass
```

---

### 4. Pages/Static Deploy 模組 (PageManager)
```python
class PageManager:
    def create_page(self, project_name: str) -> Dict[str, Any]:
        """建立一個新的 Pages 專案"""
        pass

    def deploy_page(self, project_name: str, file_path: str, is_single_html: bool = True) -> Dict[str, Any]:
        """
        上傳並部署網頁，支援 Agent 自動生成的 Single-file HTML 模式。
        
        Returns:
            {
                "status": "deployed",
                "project": "falo-dashboard",
                "preview_url": "https://random-hash.falo-dashboard.pages.dev",
                "production_url": "https://falo-dashboard.pages.dev"
            }
        """
        pass
```

---

### 5. R2 儲存模組 (R2Manager)
```python
class R2Manager:
    def upload_r2(self, bucket_name: str, object_key: str, file_bytes: bytes, content_type: str) -> Dict[str, Any]:
        """
        上傳檔案或 AI 生成結果至 R2 儲存庫。
        
        Returns:
            {
                "status": "uploaded",
                "bucket": "falo-assets",
                "key": "models/ocr_v1.pth",
                "size_bytes": 104857600,
                "cdn_url": "https://assets.formosa-ai.com/models/ocr_v1.pth"
            }
        """
        pass
```

---

### 6. Workers 模組 (WorkerManager)
```python
class WorkerManager:
    def create_worker(self, name: str, script_content: str) -> Dict[str, Any]:
        """
        動態部署一個 JavaScript/TypeScript Worker 到邊緣端。
        
        Args:
            name: Worker 服務名稱 (如 "auth-gateway")
            script_content: JS 程式碼字串
            
        Returns:
            {
                "status": "active",
                "worker_name": "auth-gateway",
                "endpoint": "https://auth-gateway.formosa-ai.workers.dev"
            }
        """
        pass
```

---

## 🤖 AI-Native & Agent-Friendly 核心設計

為了確保 AI 代理人（例如搭載在系統上的自主寫碼/維運 Agent）能順利且安全地呼叫此 SDK，本藍圖包含以下專屬機制：

### 1. 自我修復與自動回退機制 (Self-Healing & Auto-Fallback)
* **情境**：Agent 呼叫 `create_dns("dev", ...)` 時，若該 DNS 已存在且被其他服務佔用，SDK 不應直接拋出 HTTP Error 中斷 Agent。
* **設計**：SDK 會回傳帶有明確衝突提示的 JSON（`{"status": "conflict", "suggested_alternative": "dev-2"}`），讓 Agent 可以直接在其推理迴圈中，自動遞增序號並重試，實現零人工干預的自動配置。

### 2. 治理與自我限速 (Agent Rate Limiting & Cost Guard)
* **防止死循環**：當 Agent 出現程式碼 Bug 陷入死循環呼叫 API 時（例如在一分鐘內重複呼叫 100 次 `upload_r2` 導致費用暴增），SDK 內置計數器：
  ```python
  # 偽代碼：內建防爆閥 (Safety Valve)
  if self.call_frequency_tracker.get_rpm() > LIMIT_THRESHOLD:
      raise AgentSafetyTriggered("偵測到異常頻繁呼叫，SDK 自動阻斷以防止產生意外費用。")
  ```
