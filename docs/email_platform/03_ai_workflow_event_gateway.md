# Module 3: AI Workflow & Enterprise Event Gateway

本模組探討如何將不同來源的通訊管道（Email, API, Webhook, LINE, File Upload）抽象化為統一的 **FALO Event Model**，並設計對接各類 SaaS / ERP 系統的 AI 自動化工作流。

---

## 1. 統一事件模型 (Unified FALO Event Model)

為了讓後端的 Python AI Runtime 與 Workflow Engine 能夠以一致的方式處理各種不同來源的事件，我們必須將原始輸入（如 MIME 郵件、LINE Webhook、API 請求）包裝成統一的事件格式。

### 📋 FALO Event Schema (JSON)

```json
{
  "eventId": "evt_9b1a2c3d4e5f6g7h8i9j",
  "timestamp": "2026-06-29T11:08:19+08:00",
  "source": "email", 
  "sender": {
    "id": "supplier@partner.com",
    "name": "捷安特股份有限公司",
    "ip": "203.0.113.5"
  },
  "recipient": {
    "id": "invoice@formosa-ai.com",
    "serviceName": "invoice_processing"
  },
  "payload": {
    "subject": "請款單_2026年6月份_捷安特",
    "bodyText": "陳小姐您好，這是本月份的請款單，再請協助安排付款，謝謝！",
    "bodyHtml": "<div>...</div>",
    "headers": {
      "message-id": "<xyz123@giant.com>",
      "spf": "pass",
      "dkim": "pass"
    },
    "attachments": [
      {
        "filename": "giant_invoice_202606.pdf",
        "mimeType": "application/pdf",
        "sizeBytes": 1048576,
        "storageUrl": "r2://attachments/giant_invoice_202606.pdf"
      }
    ]
  },
  "context": {
    "traceId": "trace_cf_edge_001",
    "retryCount": 0
  }
}
```

- **統一性**：無論是來自 LINE 的訊息（`source: "line"`）、來自網頁上傳的發票（`source: "web_upload"`）抑或 Email，其事件主體均遵循此 Schema。
- **追蹤性**：利用 `traceId` 追蹤事件從邊緣進入、AI 處理、直到寫入 ERP 與發送 LINE 通知的整個生命週期。

---

## 2. 核心 AI Workflow 流程設計

基於 FALO Event Model，我們設計了以下典型企業 AI 工作流（Workflows）：

```
[ Email Event ] ──> [ Event Validator ] ──> [ AI Processor (LLM/OCR) ] ──> [ Enterprise Connector ] ──> [ System Log & Notification ]
```

### 💼 六大 AI 工作流實踐路徑

#### 1. `invoice@` 流程：自動進帳單核銷
$$\text{Email Attachment (PDF/Image)} \longrightarrow \text{OCR + LLM Extraction} \longrightarrow \text{ERP Connector} \longrightarrow \text{LINE Financial Group Notification}$$
- **AI 處理**：提取發票號碼、金額、品名與統編。
- **整合決策**：自動比對 ERP 採購單（PO），若金額與品名相符，則直接建立 ERP 付款單草稿，並回信給供應商確認收到。

#### 2. `meeting@` 流程：會議追蹤與指派
$$\text{Voice/Text Input} \longrightarrow \text{Whisper (STT) + Summary Agent} \longrightarrow \text{Action Items Extraction} \longrightarrow \text{Google Calendar \& Sheets}$$
- **AI 處理**：辨識會議內容，提取 Action Items 與對應負責人。
- **整合決策**：在 Google Sheets 建立追蹤卡，同時向各負責人的 LINE 發送私訊提報待辦與時限。

#### 3. `audit@` 流程：風險合規自動稽核
$$\text{Contract Word/PDF} \longrightarrow \text{RAG Clause Analysis} \longrightarrow \text{Risk Assessment Generation} \longrightarrow \text{Compliance Dashboard}$$
- **AI 處理**：檢查合約條款是否踩到企業法規紅線。
- **整合決策**：將稽核結果產出為 HTML 報告，上傳至 Cloudflare Pages 生成預覽連結，並通知法務主管。

#### 4. `support@` 流程：智慧客服分流與回覆
$$\text{Customer Email} \longrightarrow \text{Sentiment \& Topic Classification} \longrightarrow \text{RAG Knowledge Retrieval} \longrightarrow \text{Auto-Reply / CRM Ticket}$$
- **AI 處理**：判斷客戶情緒（怒/平靜）與問題分類，自動查詢 FAQ 庫生成回覆信件。
- **整合決策**：同步在 CRM 系統（如 Salesforce 或 HubSpot）建立工單，若情緒為「憤怒」，立即將工單層級拉高並通知人工作服。

#### 5. `resume@` 流程：HR AI 篩選
$$\text{Resume PDF} \longrightarrow \text{Profile Parsing} \longrightarrow \text{JD Similarity Match} \longrightarrow \text{ATS / HR Tracker Sheet}$$
- **AI 處理**：結構化履歷，依據學經歷、技能與職缺匹配度打分。
- **整合決策**：將符合條件的履歷自動分類歸檔至 Google Drive，並將關鍵資訊登載至 HR Sheets。

#### 6. `translate@` 流程：商務無障礙翻譯
$$\text{Foreign Language Email} \longrightarrow \text{LLM Translation} \longrightarrow \text{Contextual Draft Response} \longrightarrow \text{Sender Gmail Drafts}$$
- **AI 處理**：高品質商業翻譯，保留原文格式。
- **整合決策**：直接調用 Google Gmail API，在寄件人的「草稿匣」中生成翻譯好的回信草稿。

---

## 3. SaaS / ERP 系統整合判斷與決策指引

針對 ERP 與 SaaS 公司的整合，我們將系統區分為 **「API 原生（API-Active）」** 與 **「傳統/封閉（API-Passive）」** 兩種類型，並提供對應的整合策略：

```
                           ┌─────────────────────────────┐
                           │   ERP / SaaS System Type    │
                           └──────────────┬──────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
      【 API 原生 (API-Active) 】                     【 傳統 / 封閉 (API-Passive) 】
   - 具備 Webhook 與 RESTful API                  - 無 API，或僅支援資料庫/檔案對接
   - 提供 SDK 與標準認證 (OAuth2)                 - 通常部署於企業內網 (On-Premise)
                  │                                               │
                  ▼                                               ▼
        [ 🤖 直連整合 Webhook ]                         [ 🛡️ 中介 / Tunnel / RPA 整合 ]
```

### 1. API 原生系統 (如 Salesforce, Dynamics 365, Modern SaaS ERP)
- **整合模式**：**Webhook 直連 / API 主動推送**。
- **實作方式**：
  1. FALO AI Runtime 解析完事件後，直接呼叫 SaaS 的 RESTful API（例如 `POST /api/v1/invoices`）。
  2. 使用 OAuth2 或 API Key 進行邊緣端安全認證。
  3. 利用 Webhook 接收 SaaS 系統的反饋（例如：「此發票已被主管拒絕，請 AI 發信重新向廠商要檔案」），觸發下一階段 AI Workflow。

### 2. 傳統 / 封閉型 ERP 系統 (如傳統 On-Premise 系統)
- **整合模式**：**中介資料表 (Staging Table) / 檔案交換 (ETL) / RPA 機器人**。
- **實作方式**：
  - **方法 A：中介資料庫同步 (推薦)**
    - FALO AI Runtime 透過 **Cloudflare Tunnel** 安全連線至企業內網的 Read-Write Replica 資料庫。
    - 將解析出的發票結構化數據，寫入雙方約定好的「中介資料表 (Staging Table)」，例如 `STG_INCOMING_INVOICES`。
    - ERP 內部的排程（Stored Procedure）定時掃描此表，將驗證通過的資料轉載入 ERP 主檔。這種方式對舊 ERP 的衝擊最低，安全性最高。
  - **方法 B：SFTP 檔案交換 (CSV/XML)**
    - 很多舊型 ERP 僅能匯入特定格式的 CSV 或 XML 檔案。
    - FALO Python Runtime 可自動將 Event 轉為標準 CSV，透過 SFTP 上傳至指定目錄，觸發 ERP 匯入精靈。
  - **方法 C：RPA (Robotic Process Automation) 協同**
    - 若 ERP 系統完全沒有任何外部匯入途徑，可由 FALO 提供 API，由企業內部的 RPA 機器人定期從 FALO 提取結構化事件，模擬人工鍵盤滑鼠操作，輸入 ERP 畫面。
