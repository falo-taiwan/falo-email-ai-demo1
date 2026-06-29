# Module 1: Email 2.0 角色定義與 AI Email Service

本模組深入探討將 Email 從「人際通訊工具」升級為「企業事件閘道（Enterprise Event Gateway）」的架構哲學，並定義如何將每一個 Email 地址轉化為獨立的 AI 服務（AI Email Services）。

---

## 1. Email 的角色重新定義：從 Communication Tool 到 Enterprise Event Gateway

在傳統企業資訊架構中，Email 扮演的是「非即時通訊工具」角色。然而，在 AI 原生（AI-Native）的時代，我們將其重新定義為**企業事件的通用入口**。

### 📊 Email 1.0 vs Email 2.0 比較

| 維度 | Email 1.0 (傳統通訊) | Email 2.0 (AI 事件閘道) |
| :--- | :--- | :--- |
| **主要定位** | 人與人（Human-to-Human）的溝通管道 | 人/系統與 AI（Human/System-to-AI）的閘道 |
| **終端處理者** | 人類員工（手動閱讀、分類、輸入系統） | AI Agent（自動解析、執行工作流、通知相關人） |
| **處理時效** | 數小時至數天（受限於人類上班時間） | 幾秒至數分鐘（自動化即時處理） |
| **資料結構化** | 非結構化（主旨、內文、附件需人工整理） | 自動結構化（MIME 解析成 JSON，LLM 提取 Key-Value） |
| **系統邊界** | 孤立的收件匣（Mailbox Silo） | 企業級 Event Hub，連接 ERP、LINE、Workspace |
| **維護成本** | 需為每位員工購買收件匣授權（高成本） | 使用免費別名（Alias）與 Workers，近乎零新增成本 |

### 🔄 演進軌跡 (Evolution Path)

1. **Email 1.0 (傳統模式)**：
   $$\text{User Send} \longrightarrow \text{Mail Server (Gmail/Exchange)} \longrightarrow \text{Mailbox Inbox} \longrightarrow \text{Human Action (Read \& Process)}$$
   *痛點*：高人力耗費、重複登入、效率低下、舊系統資料手動輸入容易出錯。

2. **Email 2.0 (AI 邊緣路由模式)**：
   $$\text{User Send} \longrightarrow \text{Cloudflare Email Routing} \longrightarrow \text{Email Worker (JS)} \longrightarrow \text{FALO AI Event Gateway} \longrightarrow \text{Python Agent/Workflow} \longrightarrow \text{Target (ERP/LINE/Sheets)}$$
   *優勢*：使用者不需要學習任何新工具，也無需改變發信習慣；AI 在後台完成一切，舊系統（如不支援 API 的舊 ERP）免改動即完成 AI 升級。

---

## 2. AI Email Service：一個 Email 地址，就是一個 AI Function

在 FALO AI Email Platform 中，我們將 **「Email Address」** 映射為 **「AI Function/Service」**。企業內部的每一個功能型信箱，都代表著一個獨立的 AI Agent 工作流。

以下為 FALO 規劃的標準 AI Email Address 矩陣：

### 🛠️ 標準服務信箱矩陣與 AI 行為定義

#### 1. 發票與單據處理：`invoice@company.com` / `ocr@company.com`
* **AI 任務**：發票解析、合約/單據圖像文字辨識與結構化。
* **輸入**：Email 附件（PDF、JPG、PNG 格式的發票或收據）。
* **AI 工作流**：
  1. Worker 偵測到附件，將檔案上傳至 **Cloudflare R2** 儲存。
  2. 觸發 Python OCR 模組提取單據上的文字與表格。
  3. LLM 根據企業 Prompt 提取關鍵欄位：`統編`、`發票號碼`、`交易日期`、`品名`、`總金額`、`稅額`。
  4. 進行 SaaS/ERP 系統整合判斷（詳見 [Module 3](03_ai_workflow_event_gateway.md)），若為 ERP 可接受格式，則透過 Webhook 寫入 ERP 暫存檔。
  5. 發送 LINE 訊息通知財務人員：「已自動解析來自 [廠商名稱] 的發票，金額 $XXX，請點此審核：[連結]」。

#### 2. 會議摘要與逐字稿：`meeting@company.com`
* **AI 任務**：會議記錄彙整、摘要生成、待辦清單（To-do List）提取。
* **輸入**：Email 內文（手寫草稿）或附件（語音檔 MP3/WAV、會議文字紀錄）。
* **AI 工作流**：
  1. 若為語音檔，先透過 Whisper API / 語音轉文字服務生成逐字稿。
  2. LLM 進行語意段落分割，整理出：「會議主題」、「決議事項」、「待辦執行人與 Deadline」。
  3. 自動將整理好的會議記錄寫入 **Google Docs**，並在 **Google Sheets** 中為相關執行人新增待辦項目。
  4. 發送郵件回覆給所有與會者，並同步發送至部門 LINE 群組。

#### 3. 企業合規與 AI 稽核：`audit@company.com`
* **AI 任務**：合約條款風險審查、報銷憑證合理性稽核。
* **輸入**：Email 內文說明與合約草案（Word/PDF）或費用報銷明細。
* **AI 工作流**：
  1. 讀取合約內容，比對企業合約範本庫（透過 RAG 檢索）。
  2. 偵測風險條款（如：無限期保密協議、不合理的罰則、付款條件衝突）。
  3. 生成「AI 稽核報告」，以紅黃綠燈標示風險等級，並回信給寄件者：「已完成初審，發現 2 處潛在風險，請檢閱附件報告」。

#### 4. 履歷解析與人才篩選：`resume@company.com`
* **AI 任務**：HR 履歷解析、技能標籤提取、職缺配對度評估。
* **輸入**：求職者投遞的履歷附件（PDF、Word）。
* **AI 工作流**：
  1. 抽取履歷文字，結構化為求職者 Profile（姓名、學歷、工作年資、專業技能）。
  2. 根據目前企業開放的職缺描述（JD）進行 LLM 評分與配對。
  3. 自動將求職者資料寫入 **Google Sheets**（HR 追蹤表）。
  4. 若配對分數高於 80 分，自動向面試官發送 LINE 通知，並透過 Calendar API 發送面試時間預約。

#### 5. 多國語言翻譯：`translate@company.com`
* **AI 任務**：多語系商務郵件自動翻譯與回信草稿生成。
* **輸入**：外語郵件（如日文、英文、德文）。
* **AI 工作流**：
  1. 自動偵測郵件語系。
  2. 翻譯為企業指定的母語（如繁體中文）。
  3. 根據上下文，自動生成母語與對應外語的回信草稿（Draft）。
  4. 回信給寄件人，讓寄件人可以「一鍵複製」或在 Gmail 草稿匣中直接點擊發送。

#### 6. 企業知識庫檢索：`km@company.com` / `pm@company.com`
* **AI 任務**：根據企業內部知識庫解答問題，或者回報專案進度。
* **輸入**：問答查詢（例如：「公司的加班費申報規定是什麼？」）。
* **AI 工作流**：
  1. 提取查詢字詞，在 Google Drive / NotebookLM 中的企業知識文件進行向量檢索（RAG）。
  2. 彙整出精準解答，並附上參考文件來源網址（file link）。
  3. 自動以郵件回覆給提問員工。

---

## 3. 「無痛升級」的核心設計：適應既有工作流

在此架構下，企業員工和外部合作夥伴的行為完全不變：
* **外部供應商**：依然將發票寄到 `invoice@yourcompany.com`。
* **面試者/獵頭**：依然將履歷寄到 `resume@yourcompany.com`。
* **業務人員**：將客戶的日文需求信「轉寄」到 `translate@yourcompany.com`。

這極大地降低了企業推動 AI 數位轉型的「摩擦阻力」。AI 扮演的是一個**全天候、零失誤、運行於邊緣的數位助理**。
