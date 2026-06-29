# Module 2: Cloudflare Email Routing & Workers 最佳實踐

本模組深入研究 Cloudflare Email Routing 的設定與限制，以及如何編寫 Email Worker 以程式化地解析、過濾並處理由邊緣路由進來的電子郵件。

---

## 1. Cloudflare Email Routing 深度研究

Cloudflare Email Routing 是一項免費且高效的郵件路由服務，能將自訂網域的郵件無縫轉發至目的地信箱。

### ⚙️ 核心路由模式與機制

1. **Email Aliases (別名路由)**：
   - 建立精確的一對一或一對多轉寄規則。例如：將 `info@formosa-ai.com` 轉寄至主管與助理的真實 Gmail 信箱。
   - **優點**：極度精確，安全性高。
   - **缺點**：每當需要新增一個別名時，需透過 Cloudflare Dashboard 或 API 進行設定。

2. **Catch-all (全捕獲路由)**：
   - 將所有未明確設定別名規則的郵件，全部路由至同一個目的地（如某個主信箱或 Email Worker）。
   - **優點**：靈活性極高。例如員工可以任意創造 `client_a_invoice@yourcompany.com` 而不需事先設定，AI 能自動在後台進行動態解析。
   - **缺點**：容易遭受垃圾郵件攻擊（Spam Harvesting）。必須搭配 SPF/DKIM/DMARC 檢驗與 Email Worker 的邊緣過濾機制。

3. **Destination Address (目的地驗證)**：
   - 轉寄的目的地信箱必須通過驗證。Cloudflare 會發送驗證信，收件者點擊連結後方可啟用轉寄。
   - 轉寄至 Email Worker 時，則**不需要**驗證目的地信箱，因為郵件是在邊緣端由代碼直接消費。

### ⚠️ 限制與最佳實踐 (Limits & Best Practices)

- **免費額度限制**：
  - Cloudflare Email Routing 目前無嚴格的每日發信量限制，但受限於 Cloudflare 全球 Edge 的 Rate Limit。
  - 對於超大規模的企業收信（如每日數十萬封），應考慮在 MX 層面部署 WAF 規則。
- **發信源認證限制 (SPF/DKIM/DMARC)**：
  - 當 Cloudflare 轉寄郵件時，它會利用 **SRS (Sender Rewriting Scheme)** 來重寫寄件者地址，以確保轉寄的郵件不會被目的地的郵件伺服器（例如 Gmail）判定為垃圾信。
- **最佳安全配置**：
  - 強烈建議在網域 DNS 中正確配置 `SPF`、`DKIM` 和 `DMARC` 記錄，保障網域的寄信信用額度。

---

## 2. Cloudflare Email Workers 技術解析

Email Workers 允許開發者編寫 JavaScript 來直接攔截、解析並動態路由電子郵件。

### 💻 Email Worker 核心 API 結構

當郵件抵達時，Worker 會觸發 `email` 事件，並傳入 `message` 物件。

```javascript
export default {
  async email(message, env, ctx) {
    // 1. 讀取郵件基本標頭
    const fromAddress = message.from;
    const toAddress = message.to;
    const subject = message.headers.get("subject");
    const messageId = message.headers.get("message-id");
    
    console.log(`✉️ 收到新郵件：從 ${fromAddress} 到 ${toAddress}，主旨：${subject}`);
    
    // 2. 邊緣端拒絕/回覆/轉寄邏輯
    if (fromAddress.endsWith("@spamdomain.com")) {
      // 拒絕郵件，寄件者會收到退信通知
      message.reject("We do not accept spam.");
      return;
    }

    // 3. 讀取郵件原始 MIME 數據
    const rawEmailSize = message.rawSize; // 位元組大小
    const rawEmailStream = message.raw;   // 可讀串流 (ReadableStream)
    
    // 4. 交給非同步處理（避免阻塞 Worker 響應）
    ctx.waitUntil(handleEmailProcessing(message, env));
  }
}
```

### 📦 郵件解析 (MIME Parser) 與附件處理

由於 `message.raw` 是一個原始的 MIME 格式 Stream（符合 RFC 5322），在 Worker 的輕量 JS 環境中，直接操作 Raw Stream 較為繁瑣。我們通常有兩種最佳實踐：

#### 實踐 A：邊緣端輕量解析（適用於 Worker 內直接處理）
利用開源的 `postal-mime` 庫，在 Worker 內部將 MIME 串流完整解析為 JSON 結構（包含附件的 ArrayBuffer）。
```javascript
import PostalMime from 'postal-mime';

async function handleEmailProcessing(message, env) {
  // 將 ReadableStream 轉為 ArrayBuffer
  const rawEmail = await new Response(message.raw).arrayBuffer();
  
  // 解析 MIME
  const parser = new PostalMime();
  const parsedEmail = await parser.parse(rawEmail);
  
  console.log("內文 (Text):", parsedEmail.text);
  console.log("HTML:", parsedEmail.html);
  
  // 處理附件
  if (parsedEmail.attachments && parsedEmail.attachments.length > 0) {
    for (const attachment of parsedEmail.attachments) {
      console.log(`發現附件: ${attachment.filename} (${attachment.mimeType})`);
      
      // 將附件上傳至 Cloudflare R2 進行持久化存儲
      const fileKey = `attachments/${Date.now()}_${attachment.filename}`;
      await env.ATTACHMENT_BUCKET.put(fileKey, attachment.content, {
        httpMetadata: { contentType: attachment.mimeType }
      });
      console.log(`✅ 附件已成功存儲於 R2: ${fileKey}`);
    }
  }
}
```

#### 實踐 B：整封轉發至 Python Backend（適用於複雜 OCR/AI 處理）
將 `message.raw` 透過 Multipart FormData 直接轉發至本機 Python FastAPI（經由 Cloudflare Tunnel），由 Python 端使用強大的 `email` 內建庫或 `pydantic` 進行重度解析。這可大幅節省 Worker 的 CPU Time。

---

## 3. Email Worker 邊緣端動作指令

Email Worker API 提供了三個關鍵的終端動作方法：

1. **`message.forward(destination)`**：
   - 將郵件原封不動轉寄至另一個驗證過的目的地地址。
   - **應用場景**：經 AI 過濾後，將正常郵件轉寄給人工客服。

2. **`message.reject(reason)`**：
   - 拒絕接收此郵件，並向寄件者發送退信通知（Bounce Mail），說明拒絕原因。
   - **應用場景**：封鎖垃圾郵件來源，或對未經授權的寄件者拒收。

3. **`message.reply(replyMessage)`**：
   - *（目前處於 Beta 或需搭配第三方寄信服務）*
   - 在 Worker 中直接回信。若要在 Worker 內實現完全靈活的郵件回覆，通常建議將郵件內容解析後，呼叫 **Resend API** 或 **MailChannels** 發送結構化回信，這樣能保證 100% 的發信成功率與 DKIM 簽章。
