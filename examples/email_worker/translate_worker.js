/**
 * FALO AI Email Platform - Translate Worker Prototype
 * 
 * 此 Worker 負責攔截郵件，並動態分流路由：
 * 1. 寄給 translate@formosa-ai.com：不論何種語言，一律翻譯為優雅的繁體中文，並附加原文。
 *    - 優化：若偵測到主要內容已為中文，則跳過 AI，直接退回信件並發送系統通知（零 Token 消耗）。
 * 2. 寄給 translate2@formosa-ai.com：不論何種語言，一律產出繁體中文的智能摘要與關鍵行動，並附加原文（中文信件亦支援摘要）。
 * 
 * 使用 postal-mime 解析郵件內文，呼叫 Cloudflare Workers AI (Llama 3.1) 進行處理，
 * 最後使用 Cloudflare Email Sending API 自動回信。
 */

import PostalMime from 'postal-mime';

export default {
  async email(message, env, ctx) {
    const fromAddress = message.from;
    const toAddress = message.to;
    const subject = message.headers.get("subject") || "(無主旨)";

    console.log(`✉️ 收到郵件！來源: ${fromAddress}，收信別名: ${toAddress}，主旨: ${subject}`);

    const recipient = toAddress.toLowerCase();
    let mode = "";
    let aiPrompt = "";
    let subjectPrefix = "";

    // 動態分流判定
    if (recipient.startsWith("translate2@")) {
      mode = "summary";
      subjectPrefix = `[FALO AI] Re: ${subject} (Summary)`;
      aiPrompt = `You are an expert bilingual executive assistant. Analyze the user's email input.
First, detect the language of the user input (ignore email headers, signatures, or metadata).

Produce a structured summary exactly in this markdown format:
### 📌 智能摘要 (Executive Summary)
- [Key point 1]
- [Key point 2]
- [Key point 3]

### 🎯 關鍵行動 / 待辦事項 (Action Items)
- [Action/Task 1 with deadlines or responsibilities if mentioned]
- [Action/Task 2]
(If no actions or deadlines are found in the email, write "無" under this section)

Rules:
- You must output the entire summary and actions in Traditional Chinese (繁體中文), regardless of the input language (whether the input is English, Chinese, or any other language).
- Only output the section headers and bullet points. Do NOT output any introductory text, warnings, or conversational greetings. Start directly with the first section header.
- Do NOT translate the full text. Only generate the summary and action items.`;
    } else if (recipient.startsWith("translate@")) {
      mode = "translate";
      subjectPrefix = `[FALO AI] Re: ${subject} (Translated)`;
      aiPrompt = `You are an expert translator. Translate the user's input text into elegant, natural Traditional Chinese (繁體中文).
Follow these strict translation rules:
1. No matter what language the input text is written in (including English, Japanese, French, Simplified Chinese, or Traditional Chinese), you must translate and output the entire content in Traditional Chinese (繁體中文). If the input is already in Traditional Chinese, preserve it but polish it for elegance and fluency.
2. Do NOT output anything other than the translated text. Do NOT include headers, notes, greetings, explanations, or back-translations.
3. Translate the entire text from start to finish without summarizing, omitting, or truncating any paragraphs.
4. Preserve the original formatting and paragraph structure.`;
    } else {
      console.log(`⏭️ 非 translate@ 或 translate2@ 郵件，略過處理。`);
      return;
    }

    ctx.waitUntil((async () => {
      try {
        // 1. 使用 postal-mime 解析郵件取得乾淨純文字
        const parser = new PostalMime();
        const parsed = await parser.parse(message.raw);
        
        const cleanBody = (parsed.text || "").trim();
        
        if (!cleanBody) {
          console.log("⚠️ 郵件內文為空，中止發送。");
          return;
        }

        console.log(`📝 待處理純文字內容 (前50字): ${cleanBody.slice(0, 50)}...`);

        // 2. 中文信件過濾邏輯 (僅適用於 translate@ 翻譯信箱)
        const chineseChars = cleanBody.match(/[\u4e00-\u9fa5]/g) || [];
        const isChinese = chineseChars.length > 10; // 中文字元超過 10 個即判定為中文信件

        if (recipient.startsWith("translate@") && isChinese) {
          console.log("🚫 偵測到主要內容為中文，跳過翻譯，直接退信（零 Token 消耗）。");
          await env.EMAIL.send({
            to: [{ email: fromAddress, name: "Recipient" }],
            bcc: [{ email: "formosa.ai.life@gmail.com", name: "Archive Log" }],
            from: { email: "translate@formosa-ai.com", name: "FALO AI Translator" },
            subject: `[FALO AI] 郵件未處理通知: ${subject}`,
            text: `您的郵件翻譯請求未處理，原因如下：\n\n偵測到此郵件之主要內容已為中文，系統暫不提供中文至中文的翻譯服務。\n\n若您有英文或其他外語郵件，歡迎寄送至本信箱進行翻譯。\n\n-------------------------\n本信件由 FALO AI Email Platform 自動檢測發送。`,
            html: `
              <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #fca5a5; border-radius: 12px; background-color: #fef2f2;">
                <h2 style="color: #dc2626; margin-bottom: 20px;">FALO AI 郵件處理提示</h2>
                <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #fee2e2; font-size: 16px; line-height: 1.6; color: #7f1d1d; margin-bottom: 15px;">
                  偵測到此郵件之主要內容已為<strong>中文</strong>，系統暫不提供中文至中文的翻譯服務。
                </div>
                <p style="font-size: 14px; color: #4b5563;">若您有英文或其它外語信件，歡迎隨時寄送至本信箱進行翻譯。</p>
                <hr style="border: none; border-top: 1px solid #fecaca; margin: 25px 0;">
                <p style="font-size: 12px; color: #9ca3af; text-align: center;">本郵件由 FALO AI 邊緣端 (Cloudflare Workers) 自主偵測發送，無須回信。</p>
              </div>
            `
          });
          console.log(`🚀 阻擋通知已發送至: ${fromAddress}`);
          return;
        }

        // 3. 呼叫 Cloudflare Workers AI
        // 擴展 max_tokens 至 4096 以支援長信件，並設定 temperature 為 0.3 確保高穩定度
        const aiResponse = await env.AI.run("@cf/meta/llama-3.1-8b-instruct-fast", {
          messages: [
            { role: "system", content: aiPrompt },
            { role: "user", content: cleanBody }
          ],
          max_tokens: 4096,
          temperature: 0.3
        });

        const translatedResult = (aiResponse.response || aiResponse.text || "").trim();
        
        if (!translatedResult) {
          console.log("⚠️ AI 輸出為空。");
          return;
        }
        
        console.log(`✅ AI 處理完成！模式: ${mode}，輸出長度: ${translatedResult.length} 字。`);

        // 4. 呼叫 Cloudflare Email Sending API 進行回信 (自動在下方附加原文)
        const emailTitle = mode === "summary" ? "FALO AI 智能郵件摘要" : "FALO AI 智能翻譯結果";
        const fromEmail = mode === "summary" ? "translate2@formosa-ai.com" : "translate@formosa-ai.com";

        await env.EMAIL.send({
          to: [{ email: fromAddress, name: "Recipient" }],
          bcc: [{ email: "formosa.ai.life@gmail.com", name: "Archive Log" }],
          from: { email: fromEmail, name: "FALO AI Translator" },
          subject: subjectPrefix,
          text: `${emailTitle}：\n\n-------------------------\n\n${translatedResult}\n\n-------------------------\n【以下為郵件原文 / Original Text】\n\n${cleanBody}\n\n-------------------------\n本信件由 FALO AI Email Platform 自動處理發送。`,
          html: `
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fafafa;">
              <h2 style="color: #4f46e5; margin-bottom: 20px;">${emailTitle}</h2>
              <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 16px; line-height: 1.6; color: #1e293b; white-space: pre-wrap; margin-bottom: 20px;">${translatedResult}</div>
              
              <h4 style="color: #64748b; margin-bottom: 8px;">郵件原文 (Original Text)</h4>
              <div style="background-color: #f1f5f9; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 14px; line-height: 1.5; color: #475569; white-space: pre-wrap;">${cleanBody}</div>
              
              <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 25px 0;">
              <p style="font-size: 12px; color: #64748b; text-align: center;">本郵件由 FALO AI 邊緣端 (Cloudflare Workers) 自主處理並發送，無須回信。</p>
            </div>
          `
        });

        console.log(`🚀 成功將處理結果回信給: ${fromAddress}`);

      } catch (err) {
        console.error(`❌ 工作流失敗: ${err.message}`, err);
      }
    })());
  }
};
