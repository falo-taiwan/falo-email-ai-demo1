# Module 1: Edge Platform Blueprint (Cloudflare 邊緣層最佳實踐)

本模組深入探討 Cloudflare 服務作為 FALO Edge Layer 的核心技術實踐，提供具備 AI-Native 與高擴展性的架構藍圖。

---

## 1. Cloudflare Pages 最佳架構

Cloudflare Pages 是 FALO 用於部署前端界面、AI 儀表板及靜態報表的首選平台。

### 核心特性與最佳實踐
* **Single-file HTML 部署**：適合 AI 代理人 (Agents) 動態生成單一檔案（包含 Tailwind CSS 與 Vanilla JS）並直接透過 API 部署。這種方式速度極快，且不需複雜的建置步驟。
* **GitHub 整合自動部署**：將 GitHub 專案與 Cloudflare Pages 綁定，任何 Git Push 均能觸發邊緣部署。
* **Custom Domain 與 SSL**：原生支援綁定自訂子網域名稱（如 `dev.formosa-ai.com` 或 `dashboard.formosa-ai.com`），免去憑證維護成本。
* **Branch 與 Preview 部署**：每次建立 PR 或新分支時，Cloudflare 會自動生成專屬的 Preview URL。這對 AI 代理人在進行 UI 調整與自發性測試（Agent Self-testing）時極為重要，可將 Preview URL 傳回 Agent 進行視覺回饋驗證。
* **靜態網站最佳實踐 (SPA/JAMstack)**：與 R2 結合，將大型媒體檔案放於 R2 並透過 CDN 快取，Pages 僅儲存核心邏輯（JS/CSS），確保毫秒級的載入速度。

### 🏆 FALO 推薦前端架構：
```
   [ GitHub Repo ] ──(Push/PR)──> [ Cloudflare Pages ] ──> [ 全球邊緣 Edge CDN ]
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
         [ Preview URL ] (AI Agent 測試)                 [ Production URL ]
```

---

## 2. Cloudflare Workers 職責劃分：Workers vs. Python

Workers 具備全球低延遲與冷啟動時間近乎為零的優勢，但受限於執行時間與計算庫。

### 🔄 適合與不適合用 Workers 取代 Python 的場景：

| 服務類型 | 是否適合 Workers 取代 Python | 原理與架構考量 |
| :--- | :--- | :--- |
| **HTTP API Gateway & 路由** | ✅ **適合** | 邊緣路由、CORS 處理與請求分流。Workers 在 0 毫秒冷啟動下能提供最速回應，不需經過本機 Python Web Server。 |
| **Middleware & 授權過濾** | ✅ **適合** | 在邊緣端進行 JWT 驗證、API Key 檢查與請求攔截，阻止非法請求到達 Python Runtime，節約內網頻寬與運算資源。 |
| **輕量級資料轉發 (Proxy & Redirect)** | ✅ **適合** | 將外部 webhook 或動態請求以邊緣端反向代理方式，安全導向本機的 Cloudflare Tunnel 端點。 |
| **大型 AI 推理與 OCR** | ❌ **不適合** | 邊緣 Workers 缺乏 CUDA 加速及本機大型 Python 依賴（如 PyTorch, EasyOCR），應保留在具備 GPU/NPU 的 Python 本機 Runtime。 |
| **長連接 (Long-running Tasks & WebSockets)** | ❌ **不適合** | Workers 有嚴重的 CPU Time 限制（免費版 10ms，付費版最高 50ms/30s Wall Time），長時間運算或 ETL 應交給 Python 處理。 |

---

## 3. Cloudflare Tunnel 部署最佳實踐

Tunnel 是連接 Cloudflare 邊緣與 FALO 本機 Python 服務的安全橋樑。

### ⚙️ 企業級 Tunnel 配置建議：
* **多 Tunnel (Multi-Tunnel) 隔離**：  
  依據環境（`falo-dev-tunnel`、`falo-prod-tunnel`）以及客戶專案建立獨立的 Tunnel，確保開發與生產環境完全物理隔離。
* **多副本高可用 (Multi-Replica/High Availability)**：  
  在不同的本機伺服器上以同一個 Token 啟動多個 `cloudflared` 執行個體。Cloudflare 會自動在這些副本之間實現負載平衡與故障轉移 (Failover)。
* **多 Hostname & 多 Port/Service 對應**：  
  單一 Tunnel 內可配置一對多的路由。透過設定設定檔，可將不同的域名精準導向本機的不同埠口：
  ```yaml
  tunnel: 69b19190-6dff-4156-a192-2409871ecab9
  credentials-file: /root/.cloudflared/69b19190-6dff-4156-a192-2409871ecab9.json
  ingress:
    - hostname: api.formosa-ai.com
      service: http://localhost:8000
    - hostname: ocr.formosa-ai.com
      service: http://localhost:8100
    - hostname: erp.formosa-ai.com
      service: http://localhost:8200
    - service: http_status:404
  ```
* **跨平台部署支援**：  
  FALO 提供統一的執行腳本，支援 macOS (ARM/Intel)、Linux、Windows，並強烈建議在生產環境中使用 **Docker** 部署以利 Agent 自動化水平擴充：
  ```bash
  docker run -d --name falo-tunnel cloudflare/cloudflared:latest tunnel --no-autoupdate run --token <TOKEN>
  ```

---

## 4. Cloudflare R2 儲存治理與跨平台比較

R2 提供零輸出費用（Zero Egress Fees）的 S3 相容物件儲存，是 FALO AI 模型權重、大量圖像與音訊資料的首選庫。

### 📊 物件儲存媒介比較：

| 維度 | Cloudflare R2 | Google Drive | GitHub Releases |
| :--- | :--- | :--- | :--- |
| **主要定位** | 生產級 API 存取與全球 CDN 快取 | 團隊文件協作與人機共享知識庫 | 程式碼版本控制與編譯產物發布 |
| **API 友善度** | ★★★★★ (標準 AWS S3 SDK) | ★★★☆☆ (需複雜 OAuth2 認證) | ★★★★☆ (GitHub API 限流) |
| **傳輸成本 (Egress)** | **$0 / GB (完全免費)** | 計入 Google Workspace 容量 | 免費，但有 API 速率限制 |
| **適用的 FALO 資料** | AI 訓練集、OCR 生成檔案、音訊 raw data | 團隊提示詞手冊、SOP 流程、Excel 報表 | 靜態 `cloudflared` 二進位檔、CLI 工具 |

---

## 5. Cloudflare D1 邊緣資料庫定位

D1 是基於 SQLite 的邊緣關聯式資料庫，具備極低的讀取延遲與輕量特性。

### 適合與不適合 D1 儲存的資料類型：

```
                           ┌─────────────────────────────┐
                           │      FALO Data Layer        │
                           └──────────────┬──────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
      【 ✅ 適合存於 D1 】                            【 ❌ 不適合存於 D1 】
  - Prompt Templates (版本控制)                   - Vector Embeddings (向量檢索)
  - Config / Feature Flags (全域設定)            - Raw OCR Images / Audio (體積過大)
  - Session States (用戶對話狀態)                 - Real-time High QPS Audit Logs
  - API Gateway 存取白名單                        (D1 免費額度限制寫入頻率)
```

---

## 6. Cloudflare Zero Trust 安全治理

為了保護 FALO Cloud Platform 的內部管理系統（如 `admin.formosa-ai.com`），我們採用 Zero Trust (Access) 代替傳統 VPN。

### 🛡️ 企業安全保護措施：
1. **認證整合 (IdP)**：串接 Google Workspace，僅允許 `@formosa-ai.com` 網域的企業信箱登入。
2. **裝置檢測 (Device Posture)**：檢查請求端點是否安裝企業防毒軟體、防火牆是否開啟、是否為授權的 Mac 裝置。
3. **無密碼防護 (One-Time PIN)**：支援動態傳送 PIN 碼，防止因密碼洩漏導致系統被入侵。

---

## 7. Cloudflare AI Gateway 平台層定位

AI Gateway 提供統一的 LLM 代理與治理能力。

### 💡 對 FALO 的核心價值：
* **多模型支援**：統一封裝 OpenAI, Claude, Gemini 的 API 呼叫。對本機 Python Agent 來說，它只需要呼叫 Cloudflare 端點，其餘由 Gateway 進行負載平衡與失敗轉送 (Failover)。
* **邊緣端快取 (Edge Caching)**：重複的 Prompt 請求（例如：重複測試同一個 OCR 分析）可以直接在邊緣端回傳快取的 LLM 回應，省去昂貴的 Token 成本。
* **Token 限流與成本監控**：集中統計 FALO 各專案的 Token 消耗，提供 Audit Log，追蹤 AI Agent 是否陷入死循環呼叫。
