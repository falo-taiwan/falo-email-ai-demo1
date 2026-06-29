#!/usr/bin/env python3
"""
FALO AI Email Platform - Python FastAPI Event Handler Backend
这是一个基于 FastAPI 的后台原型代码。
它负责接收来自 Cloudflare Email Worker 的结构化事件 (FALO Event Model JSON)，
根据收件地址分发至对应的 AI Service，执行模擬的 AI OCR、LLM 摘要或翻譯，
并模擬写入 ERP 系統與發送 LINE 通知。
"""

import sys
import os
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

app = FastAPI(
    title="FALO AI Email Platform - Event Handler",
    description="接收來自 Cloudflare Email Worker 的邊緣事件，進行 AI 分析與 ERP 寫入的後端伺服器",
    version="1.0.0"
)

# ----------------------------------------------------------------------
# 1. Pydantic 數據模型定義 (FALO Event Model)
# ----------------------------------------------------------------------

class SenderInfo(BaseModel):
    id: str = Field(..., description="寄件者 Email 地址")
    name: str = Field(..., description="寄件者顯示名稱")

class RecipientInfo(BaseModel):
    id: str = Field(..., description="收件者別名 Email 地址")
    serviceName: str = Field(..., description="對應的 AI 服務模組名稱")

class AttachmentInfo(BaseModel):
    filename: str
    mimeType: str
    sizeBytes: int
    storageUrl: str = Field(..., description="附件在 Cloudflare R2 中的路徑")

class EventPayload(BaseModel):
    subject: str
    bodyText: str
    headers: Dict[str, str]
    attachments: List[AttachmentInfo] = []

class EventContext(BaseModel):
    traceId: str
    retryCount: int = 0

class FaloEvent(BaseModel):
    eventId: str
    timestamp: str
    source: str = "email"
    sender: SenderInfo
    recipient: RecipientInfo
    payload: EventPayload
    context: EventContext

# ----------------------------------------------------------------------
# 2. 邊緣驗證 Middleware (安全機制)
# ----------------------------------------------------------------------
FALO_SECRET_SIGNATURE = "falo_secret_sig_key_2026"

def verify_signature(x_falo_signature: Optional[str] = Header(None)):
    if not x_falo_signature or x_falo_signature != FALO_SECRET_SIGNATURE:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid X-FALO-Signature header"
        )

# ----------------------------------------------------------------------
# 3. Webhook 核心路由 (Event Gateway Entry)
# ----------------------------------------------------------------------

@app.post("/v1/email-webhook", response_model=Dict[str, Any])
async def receive_email_webhook(event: FaloEvent, x_falo_signature: Optional[str] = Header(None)):
    # 驗證來自 Cloudflare Worker 的簽名
    verify_signature(x_falo_signature)
    
    trace_id = event.context.traceId
    service_name = event.recipient.serviceName
    sender_mail = event.sender.id
    
    print(f"\n📥 [Backend] 收到事件 {event.eventId} (Trace: {trace_id})")
    print(f"   來源別名: {event.recipient.id} -> 驅動服務: {service_name}")
    print(f"   寄件者: {sender_mail} | 主旨: {event.payload.subject}")
    
    # 根據 serviceName 進行 AI 工作流分流
    response_data = {"status": "accepted", "traceId": trace_id}
    
    if service_name == "invoice_processing":
        response_data.update(await process_invoice_workflow(event))
    elif service_name == "meeting_summary":
        response_data.update(await process_meeting_workflow(event))
    elif service_name == "language_translation":
        response_data.update(await process_translation_workflow(event))
    elif service_name == "hr_screening":
        response_data.update(await process_hr_workflow(event))
    else:
        response_data.update(await process_general_workflow(event))
        
    return response_data

# ----------------------------------------------------------------------
# 4. 模組化 AI Workflow 實作 (模擬 AI 計算與整合)
# ----------------------------------------------------------------------

async def process_invoice_workflow(event: FaloEvent) -> Dict[str, Any]:
    """invoice@ 流程：OCR 解析 + 寫入 ERP 中介表 + LINE 通知"""
    print("🤖 [AI Workflow] 啟動發票辨識處理流...")
    
    # 模擬 R2 附件下載與 OCR
    if event.payload.attachments:
        target_attachment = event.payload.attachments[0]
        print(f"   ├─ 從 R2 獲取檔案: {target_attachment.storageUrl}")
        print(f"   ├─ 呼叫 OpenCV/EasyOCR 引擎分析結構...")
        print(f"   ├─ 呼叫 LLM 提取發票欄位...")
        
        # 模擬結構化欄位
        invoice_fields = {
            "vendor_name": "捷安特股份有限公司",
            "invoice_number": "AB-12345678",
            "date": "2026-06-25",
            "total_amount": 54600,
            "tax": 2600
        }
        print(f"   ├─ 解析成功! 欄位: {invoice_fields}")
        
        # 模擬 ERP 整合決策 (傳統中介表模式)
        print("   ├─ [SaaS/ERP Integration Decision] 檢測到系統為 API-Passive 傳統 ERP")
        print("   ├─ 連接本地資料庫，寫入 STG_INCOMING_INVOICES 表...")
        print("   │  SQL: INSERT INTO STG_INCOMING_INVOICES (Vendor, InvNum, Amount) VALUES (?, ?, ?)")
        print("   ├─ 數據寫入 ERP 暫存檔成功。")
        
        # 模擬 LINE 訊息發送
        print(f"   └─ 呼叫 LINE Notify: [財務通知] 捷安特發票解析成功，金額 ${invoice_fields['total_amount']}，已匯入 ERP，請點此核審。")
        
        return {
            "processed": True,
            "module": "invoice_ocr",
            "extractedFields": invoice_fields,
            "erpSyncStatus": "success",
            "lineNotified": True,
            "autoReply": True,
            "replyMessage": "您的發票 (AB-12345678) 已成功上傳並進入 ERP 審核流程，系統案號為 #1088。"
        }
        
    return {"processed": False, "reason": "No attachment found"}

async def process_meeting_workflow(event: FaloEvent) -> Dict[str, Any]:
    """meeting@ 流程：會議整理 + 寫入 Google Sheets / Docs"""
    print("🤖 [AI Workflow] 啟動會議記錄與待辦清單分析...")
    body_text = event.payload.bodyText
    
    # 模擬 LLM 摘要
    summary_text = "本次會議決議本週三前將 FALO AI Email 原型部署至測試環境。"
    action_items = [
        {"owner": "Force", "task": "部署 Email Worker 原型", "deadline": "2026-07-01"}
    ]
    print(f"   ├─ 摘要整理: {summary_text}")
    print(f"   ├─ 提取 Action Items: {action_items}")
    
    # 寫入 Google Sheets
    print("   ├─ [Google Workspace Integration] 使用 Service Account 連線 Google Sheets API")
    print(f"   ├─ 寫入 Sheet: 'FALO_Project_Tasks' -> 新增 Task: {action_items[0]['task']}")
    print("   └─ 呼叫 LINE API 通知負責人 Force。")
    
    return {
        "processed": True,
        "module": "meeting_summary",
        "actionItemsCreated": len(action_items),
        "googleSheetsSynced": True
    }

async def process_translation_workflow(event: FaloEvent) -> Dict[str, Any]:
    """translate@ 流程：多國語言翻譯 + 建立 Gmail 草稿"""
    print("🤖 [AI Workflow] 啟動多語系自動翻譯...")
    print(f"   ├─ 檢測語言... (自動檢測為 繁體中文)")
    print(f"   ├─ 將郵件主旨翻譯為英文...")
    print(f"   ├─ [Google Workspace Integration] 使用 Gmail API 在寄件人郵件帳戶中建立草稿")
    print(f"   └─ 草稿已成功放入寄件人 Gmail Draft Box！")
    
    return {
        "processed": True,
        "module": "translation",
        "draftCreated": True,
        "languagePair": "zh-tw -> en"
    }

async def process_hr_workflow(event: FaloEvent) -> Dict[str, Any]:
    """resume@ 流程：履歷結構化 + 技能比對 + Sheets 登記"""
    print("🤖 [AI Workflow] 啟動求職履歷解析...")
    print(f"   ├─ 解析 R2 履歷附件 PDF...")
    print(f"   ├─ 比對職缺關鍵字 (Python, LLM, Cloudflare)...")
    print(f"   ├─ 評分比對度為: 88分")
    print(f"   ├─ [Google Workspace Integration] 寫入 HR 招募追踪 Excel...")
    print(f"   └─ 呼叫 LINE 發送面試邀請建議通知予 HR 部門主管。")
    
    return {
        "processed": True,
        "module": "hr_screening",
        "score": 88,
        "hrTrackerSynced": True
    }

async def process_general_workflow(event: FaloEvent) -> Dict[str, Any]:
    """一般事件路由"""
    print("🤖 [AI Workflow] 執行一般郵件事件分流...")
    return {
        "processed": True,
        "module": "general_routing",
        "logSaved": True
    }

# ----------------------------------------------------------------------
# 5. 本地測試入口
# ----------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("-----------------------------------------------------------------")
    print("🚀 Starting FALO AI Email Platform Event Handler server locally...")
    print(f"📡 Webhook URL: http://localhost:{port}/v1/email-webhook")
    print("-----------------------------------------------------------------")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
