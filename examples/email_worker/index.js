/**
 * FALO AI Email Platform - Cloudflare Email Worker Prototype
 * 
 * 此 Worker 負責在邊緣端直接攔截 incoming 郵件，進行 SPF/DKIM 身分與安全檢查，
 * 解析郵件標頭，將附件串流上傳至 Cloudflare R2，最終打包成 FALO Event Model JSON
 * 並傳送至本地的 Python AI Runtime (經由 Cloudflare Tunnel)。
 */

// 導入 MIME 解析庫 (若要在邊緣解析，建議在 wrangler.toml 中打包此 npm 模組)
// 在本地開發或無 node_modules 時，可用以下示範的輕量解析模式
// import PostalMime from 'postal-mime';

export default {
  async email(message, env, ctx) {
    const messageId = message.headers.get("message-id") || `msg_${Date.now()}`;
    const fromAddress = message.from;
    const toAddress = message.to;
    const subject = message.headers.get("subject") || "(無主旨)";
    const dateStr = message.headers.get("date") || new Date().toISOString();

    console.log(`📡 [Edge] 收到 Email: ${messageId}`);
    console.log(`   寄件人: ${fromAddress}`);
    console.log(`   收件人: ${toAddress}`);
    console.log(`   主旨: ${subject}`);

    // --- 1. 安全過濾 (SPF/DKIM/DMARC 判斷) ---
    // Cloudflare 會自動在標頭中登載 SPF/DKIM 的驗證結果
    const spfResult = message.headers.get("spf") || "unknown";
    const dkimResult = message.headers.get("dkim") || "unknown";
    
    if (spfResult === "fail" || dkimResult === "fail") {
      console.warn(`⚠️ [Security Alert] SPF/DKIM 驗證失敗，潛在偽造郵件。`);
      // 可選擇拒收該郵件
      // message.reject("Security verification failed: SPF/DKIM mismatch.");
      // return;
    }

    // --- 2. 邊緣端拒收名單與轉寄規則 ---
    if (fromAddress.endsWith("@bad-spammer.com")) {
      message.reject("We do not accept mail from your domain.");
      return;
    }

    // --- 3. 處理與解析 MIME / 附件上傳 R2 ---
    // 使用 waitUntil 避免阻塞 SMTP 連線回應
    ctx.waitUntil((async () => {
      let attachmentsMetadata = [];

      try {
        // 將原始 MIME 串流轉為 ArrayBuffer
        const rawEmailArrayBuffer = await new Response(message.raw).arrayBuffer();
        
        // 模擬/呼叫 MIME 解析器
        // const parser = new PostalMime();
        // const parsedEmail = await parser.parse(rawEmailArrayBuffer);
        
        // 此處模擬解析出的附件與內文
        const mockParsedBodyText = `模擬郵件內文: 請幫我處理這張發票附件。`;
        const mockParsedAttachments = [
          {
            filename: "invoice_2026_june.pdf",
            mimeType: "application/pdf",
            // 模擬的附件二進位內容
            content: new Uint8Array([0x25, 0x50, 0x44, 0x46]) // PDF 魔術字頭 %PDF
          }
        ];

        // 遍歷附件，上傳至 Cloudflare R2
        if (env.ATTACHMENT_BUCKET && mockParsedAttachments.length > 0) {
          for (const attachment of mockParsedAttachments) {
            const fileKey = `attachments/${messageId}/${attachment.filename}`;
            
            // 將附件上傳至 R2 Bucket
            await env.ATTACHMENT_BUCKET.put(fileKey, attachment.content, {
              httpMetadata: { contentType: attachment.mimeType },
              customMetadata: {
                messageId: messageId,
                from: fromAddress,
                uploadedAt: new Date().toISOString()
              }
            });

            console.log(`✅ 附件成功上傳至 R2: ${fileKey}`);
            
            attachmentsMetadata.push({
              filename: attachment.filename,
              mimeType: attachment.mimeType,
              sizeBytes: attachment.content.byteLength,
              storageUrl: `r2://${env.ATTACHMENT_BUCKET_NAME || 'falo-bucket'}/${fileKey}`
            });
          }
        }

        // --- 4. 包裝為統一 FALO Event Model ---
        const faloEvent = {
          eventId: `evt_${messageId.replace(/[^a-zA-Z0-9]/g, "").slice(0, 16)}`,
          timestamp: new Date().toISOString(),
          source: "email",
          sender: {
            id: fromAddress,
            name: fromAddress.split("@")[0]
          },
          recipient: {
            id: toAddress,
            serviceName: determineServiceName(toAddress)
          },
          payload: {
            subject: subject,
            bodyText: mockParsedBodyText,
            headers: {
              "message-id": messageId,
              "spf": spfResult,
              "dkim": dkimResult,
              "date": dateStr
            },
            attachments: attachmentsMetadata
          },
          context: {
            traceId: `trace_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
            retryCount: 0
          }
        };

        // --- 5. 將事件 Webhook 推送至 Python AI Runtime ---
        // PYTHON_WEBHOOK_URL 可在 wrangler.toml [vars] 或環境變數中設定
        // 例如：https://api.formosa-ai.com/v1/email-webhook
        const webhookUrl = env.PYTHON_WEBHOOK_URL || "http://localhost:8000/v1/email-webhook";
        
        console.log(`🚀 推送事件至 Python AI Runtime: ${webhookUrl}`);
        
        const response = await fetch(webhookUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-FALO-Signature": "falo_secret_sig_key_2026" // 簡單的安全驗證標頭
          },
          body: JSON.stringify(faloEvent)
        });

        if (response.ok) {
          const resJson = await response.json();
          console.log(`✅ Python API 接收成功:`, resJson);
          
          // 如果後端指示需要自動回信
          if (resJson.autoReply && resJson.replyMessage) {
            // 可透過 Resend API 回信
            // await sendReplyViaResend(fromAddress, subject, resJson.replyMessage, env);
          }
        } else {
          console.error(`❌ Python API 回報錯誤: ${response.status} ${response.statusText}`);
        }

      } catch (err) {
        console.error(`❌ 郵件非同步處理失敗: ${err.message}`, err);
      }
    })());
  }
};

/**
 * 根據收信地址決定服務類型
 */
function determineServiceName(toAddress) {
  const localPart = toAddress.split("@")[0].toLowerCase();
  
  // 例外規則或別名映射
  const services = {
    ocr: "ocr_processing",
    invoice: "invoice_processing",
    meeting: "meeting_summary",
    audit: "compliance_audit",
    resume: "hr_screening",
    translate: "language_translation",
    support: "customer_support",
    km: "knowledge_management",
    pm: "project_management"
  };

  return services[localPart] || "general_email_routing";
}
