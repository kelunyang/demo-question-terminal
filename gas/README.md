# GAS 前後端（M2–M5）

「外省人在想什麼」的 Google Apps Script Web App：`Code.gs`（後端）+ `Index.html`（Vue 前端，由 HtmlService 服務）。

## 檔案

| 檔案 | 說明 |
|---|---|
| `Code.gs` | 後端：資料讀取、Gemini 代理（`generateContent` + function calling）、tool-use 資料函式、設定讀寫 |
| `Index.html` | 前端單檔：Vue 3 + Element Plus + D3.js + Font Awesome + marked（皆走 CDN），`google.script.run` 呼叫後端 |
| `appsscript.json` | manifest（時區、OAuth scopes、Web App 設定）|

## 部署步驟

### 一、準備資料
1. 執行 `data-pipeline/build_excel.py` 產生 `TNSS_harmonized.xlsx`。
2. 上傳到 Google Drive，**以 Google 試算表開啟**（或上傳時轉為 Google Sheets）。
3. 複製該試算表的 **Sheet ID**（網址 `/d/<這段>/edit`）。

### 二、建立 Apps Script 專案（擇一）

**A. 用 clasp（推薦）**
```bash
npm install -g @google/clasp
clasp login
clasp create --type webapp --title "外省人在想什麼"   # 在 gas/ 目錄執行
clasp push                                             # 上傳 Code.gs / Index.html / appsscript.json
clasp deploy                                           # 產生 Web App 部署
```
> 若 `clasp create` 產生了自己的 `appsscript.json`，用本目錄的覆蓋它。

**B. 手動**
1. 到 [script.google.com](https://script.google.com) 新增專案。
2. 貼上 `Code.gs`；新增 HTML 檔命名 `Index`（不含副檔名），貼上 `Index.html` 內容。
3. 專案設定開啟「顯示 appsscript.json manifest」，貼上本目錄 manifest。

### 三、設定 Script Properties（也可部署後從網頁齒輪填）
專案設定 → 指令碼屬性，新增：

| 屬性 | 值 |
|---|---|
| `SHEET_ID` | 步驟一複製的試算表 ID |
| `GEMINI_API_KEY` | 你的 Gemini API 金鑰 |
| `DEFAULT_PROMPT` |（可留空，程式有內建預設）|

> `GEMINI_API_KEY` 只存後端、不回傳前端；模型 `gemini-3.5-flash` 寫死於 `Code.gs`，UI 不可改。

### 四、部署為 Web App
- 部署 → 新增部署 → 類型「網頁應用程式」
- 執行身分：**我**；存取權：**任何人**（或依需求）
- 首次會要求授權 Spreadsheet 唯讀 + 外部連線（呼叫 Gemini）權限。

### 五、開啟網址
- 右上齒輪確認 `SHEET_ID`／API Key 已設定 → 選年度 → 勾議題欄位 → 看圖 + AI 描述。
- 右下角 Insight 助手可自然語言問資料（Gemini 透過 tool use 查數回答）。

## 功能對應

- **M3** 三組控制（年度單選 `el-segmented`／議題複選 `el-checkbox-button`／圖表類型單選 `el-segmented`）+ D3 圖表（X=出生年代）
- **M4** 圖表 render 後自動 `describeChart()`；出題抽屜 `generateQuiz → 作答 → gradeQuiz` 完整迴圈，Markdown render
- **M5** `fa-cog` 設定面板（Sheet ID／API Key／Default Prompt；模型唯讀）；右下角 Insight 助手（function calling）

## 疑難排解

- **初始化失敗 / 找不到年度**：多半是 `SHEET_ID` 未設定或試算表非「年度為工作表名」結構。
- **AI 相關失敗**：檢查 `GEMINI_API_KEY`，或模型配額。
- **快取**：年度資料以 `CacheService` 快取 6 小時；更新試算表後可能需等快取過期或改 Sheet 重新部署。
