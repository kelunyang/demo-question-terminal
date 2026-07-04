# 台灣的族群政治

台灣國家安全調查（TNSS, Duke University）**族群 × 世代**政治態度視覺化網站。
核心提問：**不同世代、不同族群（本省閩南／客家／外省／原住民）在兩岸關係、國族認同、
政黨傾向上，關心的重點與立場有什麼差異？**

🔗 **線上網站**：<https://script.google.com/macros/s/AKfycbwUCAflC2j-HE6cJ4hB5vo7Vjkda-mAZbGvuSD_RJGeuz3B_WuIUX7vbO162yN3k3ry/exec>

## 架構

```
SPSS 原始資料 (.sav ×16 年度)
      │  data-pipeline/  — Python 跨年度欄位語意對齊
      ▼
TNSS_harmonized.xlsx  ──(手動上傳)──▶  Google Sheet
                                            │ Sheet ID 存 PropertiesService
                                            ▼
                                   gas/  — GAS Web App
                                   ├─ Code.gs    後端：只做 Sheet 資料存取 + 設定
                                   └─ Index.html Vue3 + Element Plus + D3.js 前端
                                            │  AI 請求由前端直接發出
                                            ▼
                                   worker/  — Cloudflare Worker
                                   DeepSeek 代理（API 金鑰只存 Worker secret）
                                            ▼
                                   DeepSeek API（v4 flash / pro）
```

> **為什麼 AI 走 Cloudflare Worker 而非 GAS？**
> GAS 的 `UrlFetchApp` 有實務上難以穩定繞過的逾時天花板，長推理的 DeepSeek 呼叫會被砍。
> 因此 2026-07 起把 AI 呼叫搬到獨立 Worker，前端直連；`Code.gs` 只保留 Sheet 資料與設定存取。

## 目錄

| 路徑 | 內容 |
|---|---|
| `spec.md` / `specupgrade.md` / `issue.md` | 規格書與變更記錄 |
| `data-pipeline/` | Python 前處理（原始 `.sav` 解碼、跨年度欄位對齊、輸出 Excel）→ 見其 README |
| `gas/` | Google Apps Script 前後端 → 見其 README（含 clasp 部署步驟）|
| `worker/` | Cloudflare Worker：DeepSeek 代理 |
| `frontend/` | （預留）|

## 功能

- **視覺化**：選調查年度 → 勾議題欄位（可複選）→ 選圖表類型 → D3 繪圖（X 軸固定＝出生年代），可對欄位套用 WHERE 篩選只看特定子群體
- **AI 資料描述**：圖表繪完自動產生 100 字內客觀描述
- **AI 出題／作答／批改／審題**：完整測驗迴圈，Markdown 呈現；支援老師自製題與 AI 審題
- **Insight 助手**：浮動對話，AI 透過 tool use 查資料、並能直接操作畫面（設年度／設欄位／篩選／在圖上標記）後回答

## AI 護欄（拒答與資料無關的問題）

所有 AI 呼叫的 prompt 都集中在 `gas/Index.html`，且每一個呼叫點都掛有拒答守則，確保 AI 只處理
本站 TNSS 族群政治資料相關的任務、拒絕閒聊／寫程式／角色扮演／prompt injection 等無關請求：

- `INSIGHT_SYSTEM_PROMPT`：Insight 助手專用，**寫死、不可修改**，內含拒答守則。
- `DEFAULT_PROMPT`：描述／出題／作答／批改／審題共用，可在設定面板編輯，預設即含拒答條款。
- `TOPIC_GUARD`：**寫死、不可被 `DEFAULT_PROMPT` 覆蓋**的拒答守則，會額外注入到每一個用到
  `DEFAULT_PROMPT` 的呼叫。即使使用者把可編輯的 prompt 改掉，與資料無關的請求仍會被拒絕。

## 重點技術決策

- **選用 DeepSeek 的原因：API 費率相對便宜、成本考量**（v4 flash 輸出約 $0.28／1M tokens）
- DeepSeek 金鑰只存在 Cloudflare Worker 的 secret（`env.DEEPSEEK_API_KEY`），永不落地前端
- Worker 端鎖死 model 白名單（`flash` / `pro` tier → 實際 model ID），前端只能送 tier，不能指定任意模型
- 族群以「父親省籍」為代理變項（非受訪者自陳認同）

## 快速開始

> ℹ️ **repo 不含 TNSS 資料**（`.sav` 與 `TNSS_harmonized.xlsx` 皆受 Duke 資料使用規範約束、
> 不可再散布）。第 1 步需先自行向 Duke 取得 `.sav` 放入 `data-pipeline/raw/`，
> 詳見 `data-pipeline/README.md` 的「取得原始資料並產生 xlsx」。

1. 依 `data-pipeline/README.md` 取得 `.sav`、建 venv，執行 `build_excel.py` 產生 `TNSS_harmonized.xlsx`
2. 上傳 `TNSS_harmonized.xlsx` 到 Google Drive 轉 Google Sheet，複製 Sheet ID
3. 部署 Cloudflare Worker（`cd worker && npx wrangler deploy`），並設定金鑰：
   `npx wrangler secret put DEEPSEEK_API_KEY`
4. 依 `gas/README.md` 部署 GAS Web App，於齒輪設定面板填入 Sheet ID 與 Worker 網址

## 資料來源與限制

資料來源：[Taiwan National Security Survey (Duke University)](https://sites.duke.edu/tnss/)。
**本 repo 只提供 `.sav → xlsx` 的轉換程式，不含任何 TNSS 資料**（原始檔與衍生的微觀資料
xlsx 皆受 Duke 資料使用規範約束、不可再散布，請自行取得——見 `data-pipeline/README.md`）。
族群以父親省籍為代理、電訪對高齡／極年輕涵蓋率偏低、切世代 × 族群後兩端樣本稀少——
詳見 `data-pipeline/README.md` 與 `spec.md`。
