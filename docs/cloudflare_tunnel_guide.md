# Cloudflare Tunnel 建立指南（FALO 標準流程）

Version: v1.0
Date: 2026-06-28

---

## 目標

建立第一個 Cloudflare Tunnel，將本機服務安全發布至 Internet。

### 架構
```
Internet
    │
Cloudflare
    │
Cloudflare Tunnel
    │
localhost:8000
```

### 未來規劃
```
api.formosa-ai.com
        │
Cloudflare
        │
Tunnel
        │
Python API
```

---

## 目前狀態

- Cloudflare Account 已建立
- `formosa-ai.com` 已加入 Cloudflare
- DNS 已由 Cloudflare 接管 (GoDaddy 僅保留 Registrar 身分)
- Tunnel 已建立，名稱：`falo-dev-tunnel`
- 目前等待本機 `cloudflared` Agent 連線

---

## macOS 安裝與執行方式

本專案使用 `scripts/setup.sh` 自動下載 macOS ARM64 (Apple Silicon) 架構的 `cloudflared` 執行檔，免去 Homebrew 安裝依賴。

### 手動執行（測試用）
```bash
./scripts/run-tunnel.sh
```

或使用全域安裝：
```bash
cloudflared tunnel run --token <TOKEN>
```

### 安裝為系統背景服務（Daemon）
```bash
sudo ./bin/cloudflared service install <TOKEN>
```
* **優點**：開機自動執行、永久背景服務、不需 Terminal 常駐。

---

## 下一步：建立 Public Hostname

在 Cloudflare Tunnel 管理介面設定：
1. **Subdomain**: `dev`
2. **Domain**: `formosa-ai.com`
3. **Service**: `http://localhost:8000`

設定完成後，即可透過 `https://dev.formosa-ai.com` 存取本機的 `localhost:8000` 服務。

---

## 第二階段：多 Subdomain 對應

```
api.formosa-ai.com ──> localhost:8000
ocr.formosa-ai.com ──> localhost:8100
erp.formosa-ai.com ──> localhost:8200
mail.formosa-ai.com ──> localhost:8300
```

每個 Subdomain 可在 Cloudflare Dashboard 對應至本機不同的 Port。
