# Module 5: Python Runtime 與 Worker 職責邊界分析

本模組深入探討在 FALO AI Email Platform 中，邊緣端的 Cloudflare Workers (JavaScript Runtime) 與本機/私有雲端的 Python Runtime 之間的最佳職責邊界與協作架構。

---

## 1. 職責劃分總覽 (Boundary Map)

在 AI-Native 的架構設計中，**「讓對的技術做對的事情」**是系統效能與成本控制的關鍵。

```
                         [ 📬 傳入郵件 ]
                                │
                                ▼
         ┌─────────────────────────────────────────────┐
         │       Cloudflare Workers (Edge Layer)       │
         │  - 0ms 冷啟動、全域負載平衡、輕量級標頭過濾  │
         └──────────────────────┬──────────────────────┘
                                │ (過濾後事件 / 附件存於 R2)
                                ▼
         ┌─────────────────────────────────────────────┐
         │         Python Runtime (Core Layer)         │
         │  - OCR (EasyOCR / Tesseract)、複雜 LLM RAG   │
         │  - 企業內網 ERP 寫入、長時任務 (Celery/Async)  │
         └─────────────────────────────────────────────┘
```

---

## 2. 邊界決策矩陣 (Decision Matrix)

| 任務範疇 | 邊緣 Worker (JS/V8) | 本地/雲端 Python Runtime | 決策原理與架構考量 |
| :--- | :---: | :---: | :--- |
| **網域路由與 MX 解析** | ✅ **最適合** | ❌ 不適合 | 必須在 Cloudflare Edge 直接攔截 MX 郵件。 |
| **發信人身分檢驗 (SPF/DKIM)** | ✅ **最適合** | ⚠️ 可作為輔助 | Workers 能在邊緣端快速讀取標頭，直接拒絕（`message.reject()`）惡意或偽造的郵件，省去後端 Python 頻寬。 |
| **輕量級過濾與分流** | ✅ **最適合** | ❌ 不適合 | 根據收件地址（例如 `ocr@` 與 `translate@`）對事件進行初步導航，決定後端派發的 Queue 頻道。 |
| **MIME 附件初步拆解與上傳** | ✅ **適合** | ⚠️ 可選 | Workers 在邊緣端將附件串流直接上傳至 **Cloudflare R2**，後端 Python 只需取得 R2 URL，降低 Webhook 傳輸體積。 |
| **OCR 圖像文字辨識** | ❌ 不適合 | ✅ **最適合** | OCR（如 OpenCV、PaddleOCR 或 EasyOCR）需要高度依賴 C++ 底層庫、CUDA 顯示卡加速或重度 CPU 計算，Workers V8 沙盒無法執行此類重型庫。 |
| **RAG 向量檢索與知識庫整合** | ❌ 不適合 | ✅ **最適合** | 向量資料庫連線、Embedding 生成、知識庫檢索與 Context 拼接，在 Python 生態系中有成熟的 LangChain / LlamaIndex 支持，且記憶體消耗較大。 |
| **企業內網系統寫入 (如舊 ERP)** | ❌ 不安全/受限 | ✅ **最適合** | 許多企業 ERP 部署在內網（On-Premise），透過 Cloudflare Tunnel 與 Python 接收端直連最為安全，Workers 無法直接連入企業私有網路。 |
| **多 Agent 協作與長時工作流** | ❌ 易超時 | ✅ **最適合** | Workers 免費版限制 CPU Time 10ms，付費版最高 50ms。複雜 Agent 思考與長輪詢 Webhook 呼喚很容易被 Workers 強制中斷，必須交由 Python 異步任務處理。 |

---

## 3. 協作資料流最佳實踐 (Collaboration Flow)

我們以 `invoice@formosa-ai.com` 解析發票並寫入 ERP 為例，展示兩者的高效協作方式：

```
[寄件者] ──> (發送郵件含發票 PDF)
                │
                ▼
      [ Cloudflare Worker ]
                │
                ├── 1. 檢查 SPF/DKIM (拒絕非法來源)
                ├── 2. 解析 MIME 提取 `invoice.pdf`
                ├── 3. 將 `invoice.pdf` 寫入 R2 桶子 (`r2://invoices/xyz.pdf`)
                └── 4. 發送 JSON Webhook 予 Python 端 (僅傳送元數據與 R2 連結)
                        │
                        ▼ (透過 Cloudflare Tunnel 進內網)
              [ Python Runtime ]
                        │
                        ├── 1. 從 R2 下載該 PDF（極速，免去大檔傳輸負擔）
                        ├── 2. 呼叫 OCR Engine 辨識發票影像
                        ├── 3. LLM Agent 進行欄位結構化與檢核
                        ├── 4. 寫入企業內部 ERP 中介表
                        └── 5. 呼叫 LINE API 發送成功通知給財務主管
```

- **優勢**：
  1. **極致省錢與省時**：大檔案附件不經過 API Gateway 的 HTTP Payload 傳輸，而是利用 Cloudflare R2（免傳出費用且全球 Edge 儲存極快）做中轉。
  2. **高安全性**：Python 端不對公網暴露任何 Port，全部隱藏在 Cloudflare Tunnel 後方，僅接收來自 Workers 簽章驗證過的 Webhook。
  3. **高彈性**：邊緣 Worker 永遠處於在線狀態（0ms 冷啟動），Python Runtime 即使因本地停電或重啟短暫離線，郵件也會在 Cloudflare 隊列中自動重試，不會丟失事件。
