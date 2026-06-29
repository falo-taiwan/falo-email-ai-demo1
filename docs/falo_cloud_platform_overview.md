# FALO Cloud Platform (雲端基礎建設架構總覽)

FALO Cloud Platform 是專為 FALO AI 生態系統打造的雲端基礎建設（Cloud Foundation）。其核心設計目標是提供一個高度自動化、安全且具彈性的平台，支撐未來三年以上 FALO 多樣化 AI 代理人 (AI Agents) 與微服務的演進與部署。

---

## 📐 架構設計四大原則

本平台的所有子系統、SDK 設計與部署流程均遵循以下最高原則：

1. **AI-Native (AI 原生)**  
   所有元件的設計皆需考慮 AI 模型的執行特性（如：非同步串流、高延遲、大規模平行處理與動態 Prompt 管理）。基礎建設必須能與 AI 運算 Runtime 無縫協作。
   
2. **Agent-Friendly (代理人友善)**  
   基礎設施必須暴露結構化、可自適應的介面與工具，使 AI 代理人 (Agents) 能在具備適當授權的狀況下，自主配置、監控並修復平台資源（例如：自主新增 DNS 記錄、部署網頁或上傳靜態資源）。

3. **API-First (API 優先)**  
   所有資源的操作都必須透過標準 API 進行宣告式 (Declarative) 管理。杜絕手動在 GUI 主控台進行設定的零碎操作，確保所有變更皆能透過 FALO SDK 或自動化腳本完成。

4. **Enterprise Governance (企業級治理)**  
   建立清晰的權限劃分與安全防護。確保管理端點（如 `admin.formosa-ai.com`）的安全，並為資料的生命週期、成本控管與存取軌跡 (Audit Logs) 提供集中的治理機制。

---

## 🗂️ 基礎架構文件導覽

本架構規劃書拆分為三個核心模組：

### 🌐 [Module 1: Edge Platform Blueprint](architecture/edge_platform_blueprint.md)
* **核心內容**：詳細分析 Cloudflare 在 FALO 專案中作為 **Edge Layer** 的七大關鍵元件定位（Pages, Workers, Tunnel, R2, D1, Zero Trust, AI Gateway）。
* **重點研究**：
  * Workers 與 Python 執行環境的最佳職責邊界（哪些應由 Workers 承接，哪些不適合）。
  * 針對 AI 代理人設計的靜態與動態部署最佳實踐。
  * D1 邊緣資料庫與 R2 物件儲存的應用場景與成本治理。

### 📦 [Module 2: Cloud SDK Blueprint](architecture/cloud_sdk_blueprint.md)
* **核心內容**：FALO Cloud SDK 的 Python 介面與架構設計規格書。
* **重點研究**：
  * 面向 AI 代理人設計的 API 介面宣告（`create_dns`, `create_tunnel`, `upload_r2` 等）。
  * 錯誤恢復機制與代理人限流 (Rate Limiting) 策略。
  * SDK 的模組化組件圖 (Component Map)。

### 🗺️ [Module 3: Integration Map & Topology](architecture/integration_map.md)
* **核心內容**：FALO 三維一體整合拓撲圖 (Cloudflare × GitHub × Google Workspace × Python)。
* **重點研究**：
  * **GitHub** 作為唯一真理來源 (Source of Truth) 的自動化串接。
  * **Google Workspace**（Drive, Docs, Sheets, GAS, NotebookLM）如何作為知識層與 Edge Layer 協同運作。
  * 全域資料流、控制流與認證流 (Mermaid 圖表)。

### 📧 [Module 4: FALO AI Email Platform](email_platform/README.md)
* **核心內容**：下一代企業 AI 原生郵件平台與事件閘道架構（Enterprise Event Gateway）。
* **重點研究**：
  * **Email 2.0**：從 Communication Tool 進化為 Enterprise Event Gateway。
  * **Cloudflare Email Routing & Workers** 邊緣解析、R2 附件儲存與過濾。
  * **AI Workflows**：收據/發票自動化、會議摘要、稽核與多語翻譯。
  * **SaaS/ERP 與 Google Workspace 整合** 的架構決策與商業模式。

---

## 🚀 未來三年演進路線

```
  【階段一：基礎建設建立】(目前階段)
  - DNS 接管與第一條 Tunnel 通道 (dev.formosa-ai.com -> localhost:8080) 建立完成。
  - 完成 Cloudflare 全方位架構藍圖規劃。
         │
         ▼
  【階段二：SDK 與 API 整合】
  - 實作 FALO Cloud SDK，支援 AI 代理人透過 API 動態註冊 Tunnel 與部署靜態網頁。
  - 引入 Cloudflare Zero Trust 保護企業內網管理端點。
         │
         ▼
  【階段三：邊緣智慧與知識層打通】
  - 透過 AI Gateway 治理 FALO 內部所有 LLM 呼叫。
  - 打通 Google Workspace 知識層與 Cloudflare 邊緣快取，建構全球低延遲 AI 服務。
```
