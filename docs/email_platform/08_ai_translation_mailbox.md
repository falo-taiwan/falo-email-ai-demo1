# FALO AI Email Platform - Module 8: AI 智能雙向翻譯郵箱 (AI Translation Mailbox)

本章節介紹如何利用 Cloudflare Email Routing、Workers AI (Llama 3.1 Fast) 與 Cloudflare Email Sending API 建立 `translate@formosa-ai.com` 智能雙向翻譯郵箱，實現自動偵測語言、雙向互譯並自動回信與 BCC 備份的無伺服器 (Serverless) 架構。

---

## 1. 業務痛點與 AI 解決方案

### 傳統翻譯痛點
* **人工耗時**：外貿、國際客服或跨國團隊在收到外文郵件時，需要手動複製至翻譯軟體，翻譯後再行回覆，效率低下。
* **流程斷裂**：翻譯軟體與電子郵件系統分離，資訊無法在郵件流中自動化。

### FALO AI 解決方案
* **郵件級整合**：用戶只需將郵件發送或轉寄至 `translate@formosa-ai.com`。
* **智能雙向互譯**：Edge 端的 Worker 自動解析內文，經由 Llama 3.1 偵測語言：
  * 中文 ──> 翻譯為英文
  * 英文 ──> 翻譯為繁體中文
* **自主發信回覆**：無需人工干預，數秒內將排版美觀的翻譯結果回信給原寄件人，並同時發送 BCC 密件抄送給企業備份信箱。

---

## 2. 系統架構圖 (Mermaid)

```mermaid
sequence flow
  Sender ->> Cloudflare MX: 寄送郵件至 translate@formosa-ai.com
  Cloudflare MX ->> Email Routing: 比對路由規則 (優先權 0)
  Email Routing ->> translate-worker: 觸發 email() 處理程序
  translate-worker ->> Workers AI: 調用 llama-3.1-8b-instruct-fast 進行翻譯
  Workers AI -->> translate-worker: 回傳翻譯後純文字
  translate-worker ->> Email Sending API: 發送回信 (Bcc 備份至 Gmail)
  Email Sending API -->> Sender: 送達翻譯回信
```

---

## 3. 技術實現細節

### A. 邊緣發信設定 (Outbound Email Sending)
在 Cloudflare 中設定發信網域以通過 SPF/DKIM 驗證，防止郵件被判定為垃圾信：
1. 啟用 **【Email Service】 > 【Email Sending】**。
2. 綁定 `formosa-ai.com`，並自動生成輔助的 CNAME/MX/TXT 發信專屬 DNS 紀錄 (selector: `cf-bounce`)。

### B. Worker 資源綁定 (wrangler.toml)
```toml
name = "translate-worker"
main = "index.js"
compatibility_date = "2026-06-29"

[observability]
enabled = true  # 永久啟用邊緣日誌

[ai]
binding = "AI"  # 綁定 Workers AI 引擎

[[send_email]]
name = "EMAIL"  # 綁定原生發信服務
```

### C. 郵件地址強型態檢核 (EmailAddress Strict Typing)
Cloudflare `env.EMAIL.send` 的 C++ 底層檢核非常嚴格，傳入的收發件人必須是完整的 `EmailAddress` 物件且 `name` 欄位不可缺失或為 undefined，否則會拋出型態錯誤。
* **正確格式**：
  ```javascript
  to: [{ email: fromAddress, name: "Recipient" }]
  ```

---

## 4. 效益評估

* **零基礎設施維護成本**：完全基於 Cloudflare Edge 運行，無須租用虛擬主機 (VPS) 或維護 SMTP 伺服器。
* **近乎免費的運行成本**：使用 Workers AI 每日的免費額度或極低的 Paid 費率，相比 OpenAI API 節省 90% 以上成本。
* **極致性能**：Edge 端冷啟動近乎為零，翻譯至回信在 5 秒內完成。
