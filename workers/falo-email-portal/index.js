import HTML_CONTENT from './frontend.html';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const clientIp = request.headers.get("CF-Connecting-IP") || "127.0.0.1";

    // 1. 自動初始化 Seed 預設的超級管理員帳號
    await seedSuperUser(env);

    // 2. 靜態前端頁面首頁
    if (request.method === "GET" && path === "/") {
      return new Response(HTML_CONTENT, {
        headers: { "Content-Type": "text/html; charset=utf-8" }
      });
    }

    // 3. API 路由分發
    try {
      // A. 登入 API
      if (request.method === "POST" && path === "/api/login") {
        return await handleLogin(request, env, clientIp);
      }

      // B. 發信 API (支援以 , 分割群發)
      if (request.method === "POST" && path === "/api/send") {
        const authResult = await authorize(request, env);
        if (!authResult.authorized) {
          return jsonResponse({ success: false, message: authResult.reason }, 401);
        }
        return await handleSendEmail(request, env, authResult.username, clientIp);
      }

      // C. 帳號管理 API (僅限超級管理員 force 可操作)
      if (path === "/api/users") {
        const authResult = await authorize(request, env);
        if (!authResult.authorized) {
          return jsonResponse({ success: false, message: authResult.reason }, 401);
        }
        if (authResult.username !== "force") {
          return jsonResponse({ success: false, message: "權限不足，僅限超級管理員能管理帳號" }, 403);
        }

        if (request.method === "GET") {
          return await handleListUsers(env);
        }
        if (request.method === "POST") {
          return await handleCreateUser(request, env, clientIp);
        }
        if (request.method === "DELETE") {
          return await handleDeleteUser(url, env, clientIp);
        }
      }

      // D. 動作日誌審計 API (僅限超級管理員 force 可操作)
      if (path === "/api/logs") {
        const authResult = await authorize(request, env);
        if (!authResult.authorized) {
          return jsonResponse({ success: false, message: authResult.reason }, 401);
        }
        if (authResult.username !== "force") {
          return jsonResponse({ success: false, message: "權限不足，僅限超級管理員能讀取日誌" }, 403);
        }

        if (request.method === "GET") {
          return await handleListLogs(env);
        }
      }

      // E. 聯絡人管理 API (所有登入用戶可管理各自的個人聯絡人 - 使用 O(1) 強一致性陣列儲存)
      if (path === "/api/contacts") {
        const authResult = await authorize(request, env);
        if (!authResult.authorized) {
          return jsonResponse({ success: false, message: authResult.reason }, 401);
        }

        if (request.method === "GET") {
          return await handleListContacts(env, authResult.username);
        }
        if (request.method === "POST") {
          return await handleCreateContact(request, env, authResult.username, clientIp);
        }
        if (request.method === "DELETE") {
          return await handleDeleteContact(url, env, authResult.username, clientIp);
        }
      }

      // 4. 未匹配路由
      return new Response("Not Found", { status: 404 });

    } catch (err) {
      console.error(`💥 Server error: ${err.message}`, err);
      return jsonResponse({ success: false, message: `伺服器內部錯誤: ${err.message}` }, 500);
    }
  }
};

/**
 * 密碼 SHA-256 加密雜湊
 */
async function hashPassword(password) {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
}

/**
 * 動作審計日誌寫入器
 */
async function logAction(env, username, action, ip, details) {
  const timestamp = new Date().toISOString();
  const logKey = `log:${timestamp}`;
  const logData = { timestamp, username, action, ip, details };
  // 儲存日誌，設定 7 天過期
  await env.USERS_KV.put(logKey, JSON.stringify(logData), { expirationTtl: 604800 });
}

/**
 * 初始化 Seed 超級管理員帳號
 */
async function seedSuperUser(env) {
  const adminKey = "user:force";
  const existing = await env.USERS_KV.get(adminKey);
  if (!existing) {
    console.log("🌱 Seeding default super user 'force'...");
    const hashedPassword = await hashPassword("0922764763");
    await env.USERS_KV.put(adminKey, hashedPassword);
  }
}

/**
 * 輔助函數: 回傳 JSON Response
 */
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" }
  });
}

/**
 * 權限校驗 (Bearer Token)
 */
async function authorize(request, env) {
  const authHeader = request.headers.get("Authorization");
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return { authorized: false, reason: "遺失授權憑證 Bearer Token" };
  }
  const token = authHeader.substring(7);
  const username = await env.USERS_KV.get(`session:${token}`);
  if (!username) {
    return { authorized: false, reason: "無效或已過期的 Session 憑證" };
  }
  return { authorized: true, username };
}

/**
 * API: 登入驗證
 */
async function handleLogin(request, env, clientIp) {
  const { username, password } = await request.json();
  if (!username || !password) {
    return jsonResponse({ success: false, message: "欄位缺失" }, 400);
  }

  const userKey = `user:${username}`;
  const storedPasswordHash = await env.USERS_KV.get(userKey);
  if (!storedPasswordHash) {
    await logAction(env, username, "LOGIN_FAILED", clientIp, "登入嘗試失敗：使用者不存在");
    return jsonResponse({ success: false, message: "帳號或密碼不正確" }, 401);
  }

  const inputPasswordHash = await hashPassword(password);
  if (storedPasswordHash !== inputPasswordHash) {
    await logAction(env, username, "LOGIN_FAILED", clientIp, "登入嘗試失敗：密碼不符");
    return jsonResponse({ success: false, message: "帳號或密碼不正確" }, 401);
  }

  // 登入驗證通過，發送亂數 Token 存入 KV 期限為 1 小時 (3600秒)
  const token = crypto.randomUUID();
  await env.USERS_KV.put(`session:${token}`, username, { expirationTtl: 3600 });
  
  // 記錄成功登入日誌
  await logAction(env, username, "LOGIN_SUCCESS", clientIp, "成功登入控制台");
  
  return jsonResponse({ success: true, token, username });
}

/**
 * API: 發送郵件 (支援以 , 切割群發)
 */
async function handleSendEmail(request, env, senderUsername, clientIp) {
  const { from, to, subject, body } = await request.json();
  if (!from || !to || !subject || !body) {
    return jsonResponse({ success: false, message: "發信參數不足" }, 400);
  }

  // 限制寄信角色
  const allowedFrom = ["it@formosa-ai.com", "ai@formosa-ai.com", "fi@formosa-ai.com", "translate@formosa-ai.com"];
  if (!allowedFrom.includes(from.toLowerCase())) {
    await logAction(env, senderUsername, "SEND_EMAIL_FAILED", clientIp, `發信失敗：不合規的身分 ${from}`);
    return jsonResponse({ success: false, message: "不允許的發信身分角色" }, 400);
  }

  // 切割並清理多個收件者 Email
  const recipientList = to.split(",")
                          .map(email => email.trim())
                          .filter(email => email !== "");

  if (recipientList.length === 0) {
    return jsonResponse({ success: false, message: "請輸入有效的收件者電子郵件" }, 400);
  }

  try {
    // 判定是否是 HTML 格式
    const isHtml = body.trim().startsWith("<") && body.trim().endsWith(">");
    const htmlContent = isHtml ? body : `<div style="font-family: sans-serif; white-space: pre-wrap; font-size: 16px; line-height: 1.6; color: #1e293b;">${body}</div>`;

    console.log(`✉️ Edge Portal 發信中... ${senderUsername} 以 ${from} 寄給 ${recipientList.join(", ")}`);

    const toAddresses = recipientList.map(email => ({ email: email, name: "Recipient" }));

    await env.EMAIL.send({
      to: toAddresses,
      bcc: [{ email: "formosa.ai.life@gmail.com", name: "Archive Log" }],
      from: { email: from, name: "FALO AI Portal" },
      subject: subject,
      text: isHtml ? "請使用支援 HTML 的客戶端閱讀此郵件" : body,
      html: `
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fafafa;">
          <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #cbd5e1;">
            ${htmlContent}
          </div>
          <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 25px 0;">
          <p style="font-size: 11px; color: #94a3b8; text-align: center;">本郵件由經授權用戶於 FALO Edge Email Portal 發出，並自動密件備份至系統存檔。</p>
        </div>
      `
    });

    // 記錄發信日誌 (群發會詳細記錄名單)
    await logAction(
      env,
      senderUsername,
      "SEND_EMAIL",
      clientIp,
      `寄件: ${from} ➔ 群發收件: ${recipientList.join(", ")} | 主旨: ${subject}`
    );

    return jsonResponse({ success: true, message: "郵件成功送出！" });

  } catch (err) {
    console.error(`❌ 發信失敗: ${err.message}`, err);
    await logAction(env, senderUsername, "SEND_EMAIL_ERROR", clientIp, `發信異常: ${err.message}`);
    return jsonResponse({ success: false, message: `發信失敗: ${err.message}` }, 500);
  }
}

/**
 * API: 管理員列出所有使用者
 */
async function handleListUsers(env) {
  const listResult = await env.USERS_KV.list({ prefix: "user:" });
  const users = listResult.keys.map(key => {
    return { username: key.name.substring(5) }; // 去除 user: 前綴
  });
  return jsonResponse({ success: true, users });
}

/**
 * API: 管理員新增使用者
 */
async function handleCreateUser(request, env, clientIp) {
  const { username, password } = await request.json();
  if (!username || !password) {
    return jsonResponse({ success: false, message: "請輸入完整帳密" }, 400);
  }

  const cleanUsername = username.trim().toLowerCase();
  if (cleanUsername === "force") {
    return jsonResponse({ success: false, message: "無法覆蓋超級管理員帳號" }, 400);
  }

  const userKey = `user:${cleanUsername}`;
  const hashedPassword = await hashPassword(password);
  await env.USERS_KV.put(userKey, hashedPassword);
  
  // 記錄管理員動作日誌
  await logAction(env, "force", "CREATE_USER", clientIp, `建立新使用者帳號: ${cleanUsername}`);
  
  return jsonResponse({ success: true, message: `使用者 ${cleanUsername} 建立成功` });
}

/**
 * API: 管理員刪除使用者
 */
async function handleDeleteUser(url, env, clientIp) {
  const username = url.searchParams.get("username");
  if (!username) {
    return jsonResponse({ success: false, message: "請指定要刪除的使用者名稱" }, 400);
  }

  const cleanUsername = username.trim().toLowerCase();
  if (cleanUsername === "force") {
    return jsonResponse({ success: false, message: "超級管理員帳號不可刪除" }, 400);
  }

  const userKey = `user:${cleanUsername}`;
  await env.USERS_KV.delete(userKey);
  
  // 記錄管理員動作日誌
  await logAction(env, "force", "DELETE_USER", clientIp, `刪除使用者帳號: ${cleanUsername}`);
  
  return jsonResponse({ success: true, message: `使用者 ${cleanUsername} 已刪除` });
}

/**
 * API: 管理員查詢審計日誌
 */
async function handleListLogs(env) {
  const listResult = await env.USERS_KV.list({ prefix: "log:" });
  const keysToFetch = listResult.keys.slice(-100); // 獲取最新發生的 100 筆
  const logPromises = keysToFetch.map(async (key) => {
    const rawVal = await env.USERS_KV.get(key.name);
    try {
      return JSON.parse(rawVal);
    } catch {
      return null;
    }
  });

  const rawLogs = await Promise.all(logPromises);
  const logs = rawLogs.filter(log => log !== null);
  logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  return jsonResponse({ success: true, logs });
}

/**
 * API: 獲取登入用戶專屬聯絡人清單 (強一致性設計)
 */
async function handleListContacts(env, username) {
  const contactsKey = `contacts:${username}`;
  const rawContacts = await env.USERS_KV.get(contactsKey);
  if (!rawContacts) {
    return jsonResponse({ success: true, contacts: [] });
  }
  try {
    const contacts = JSON.parse(rawContacts);
    contacts.sort((a, b) => a.name.localeCompare(b.name, 'zh-TW'));
    return jsonResponse({ success: true, contacts });
  } catch {
    return jsonResponse({ success: true, contacts: [] });
  }
}

/**
 * API: 新增/更新登入用戶專屬聯絡人 (強一致性設計)
 */
async function handleCreateContact(request, env, username, clientIp) {
  const { name, email, remark } = await request.json();
  if (!name || !email) {
    return jsonResponse({ success: false, message: "欄位缺失：姓名與 Email 為必填" }, 400);
  }

  const cleanEmail = email.trim().toLowerCase();
  const contactsKey = `contacts:${username}`;
  
  // 1. 獲取現有聯絡人陣列
  const rawContacts = await env.USERS_KV.get(contactsKey);
  let contacts = [];
  if (rawContacts) {
    try {
      contacts = JSON.parse(rawContacts);
    } catch {}
  }

  // 2. 檢查是否重複，若重複則更新，否則新增
  const existingIndex = contacts.findIndex(c => c.email === cleanEmail);
  const contactData = {
    name: name.trim(),
    email: cleanEmail,
    remark: (remark || "").trim(),
    updatedBy: username,
    timestamp: new Date().toISOString()
  };

  if (existingIndex > -1) {
    contacts[existingIndex] = contactData;
  } else {
    contacts.push(contactData);
  }

  // 3. 寫回資料庫
  await env.USERS_KV.put(contactsKey, JSON.stringify(contacts));
  await logAction(env, username, "CREATE_CONTACT", clientIp, `新增聯絡人: ${name.trim()} <${cleanEmail}>`);
  return jsonResponse({ success: true, message: "聯絡人新增成功" });
}

/**
 * API: 刪除登入用戶專屬聯絡人 (強一致性設計)
 */
async function handleDeleteContact(url, env, username, clientIp) {
  const email = url.searchParams.get("email");
  if (!email) {
    return jsonResponse({ success: false, message: "請指定要刪除的聯絡人 Email" }, 400);
  }

  const cleanEmail = email.trim().toLowerCase();
  const contactsKey = `contacts:${username}`;
  
  // 1. 獲取現有聯絡人
  const rawContacts = await env.USERS_KV.get(contactsKey);
  if (!rawContacts) {
    return jsonResponse({ success: true, message: "聯絡人已成功刪除" });
  }

  let contacts = [];
  try {
    contacts = JSON.parse(rawContacts);
  } catch {}

  const targetContact = contacts.find(c => c.email === cleanEmail);
  const contactName = targetContact ? targetContact.name : cleanEmail;

  // 2. 過濾掉目標
  const updatedContacts = contacts.filter(c => c.email !== cleanEmail);

  // 3. 寫回資料庫
  await env.USERS_KV.put(contactsKey, JSON.stringify(updatedContacts));
  await logAction(env, username, "DELETE_CONTACT", clientIp, `刪除聯絡人: ${contactName} <${cleanEmail}>`);
  return jsonResponse({ success: true, message: "聯絡人已成功刪除" });
}
