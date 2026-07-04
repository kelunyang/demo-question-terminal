# 資料前處理管線（M1）

把 TNSS（Taiwan National Security Survey, Duke）16 個年度的 SPSS 原始資料，
跨年度欄位語意對齊後，輸出成單一 Excel 活頁簿供上傳 Google Drive。

> ⚠️ **本 repo 不含任何 TNSS 資料**。原始 `.sav` 與其衍生的 `TNSS_harmonized.xlsx`
> 都是逐筆受訪者微觀資料，受 Duke TNSS 資料使用規範約束、不可公開再散布，因此**只保留
> 轉換程式、不保留資料**。請依下方步驟自行取得資料並在本機產生 xlsx。

## 取得原始資料並產生 xlsx

1. **下載 `.sav`**：到 [Taiwan National Security Survey (Duke)](https://sites.duke.edu/tnss/data/)
   依其規範申請／下載各年度 SPSS 檔（需同意其資料使用條款）。
2. **放進 `raw/`**：把檔案命名成 `<年度>.sav`（例如 `2002.sav`、`2024.sav`）放到 `data-pipeline/raw/`。
   目前程式預期的年度見下方「涵蓋年度」。
3. **建虛擬環境並裝套件**（多數 Linux 發行版的系統 Python 是 externally-managed，需用 venv）：
   ```bash
   cd data-pipeline
   python3 -m venv .venv
   .venv/bin/pip install pyreadstat pandas openpyxl
   ```
4. **產生 xlsx**：
   ```bash
   .venv/bin/python build_excel.py   # 讀 raw/*.sav → 輸出 TNSS_harmonized.xlsx
   ```
5. 產出的 `TNSS_harmonized.xlsx` 上傳 Google Drive 轉 Google Sheet（下游 GAS 用），流程見專案根目錄 README。

## 輸出

`TNSS_harmonized.xlsx`
- 每個調查年度一個工作表（`2002`…`2025`，共 16 個）
- `_meta`：欄位說明
- `_coverage`：各年度每欄位的非空筆數（覆蓋率）

每列 = 一位受訪者（respondent-level，未預先聚合）。欄位：

| 欄位 | 說明 |
|---|---|
| `survey_year` | 調查年度 |
| `birth_year_ad` | 出生年（西元，民國年換算＋清理拒答/不合理值）|
| `birth_cohort` | 出生年代（圖表 X 軸，如 `1960s`）|
| `father_ethnicity` | 父親省籍；`大陸各省市人` = 外省 |
| `taiwan_china_identity` | 臺灣人/中國人/都是（僅 2015+ 有）|
| `unif_indep_stance` | 統獨立場（6 分類）|
| `party_id` | 政黨認同 |
| `gender` / `education` / `age_group` | 人口變項 |
| `weight` | 調查權值 |

類別欄位直接存**中文標籤**（非代碼），下游 GAS／前端無需再帶 codebook。

## 涵蓋年度

2002, 2004, 2005, 2008, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2019, 2020, 2022, 2024, 2025
（Duke 官網目前可下載者；2018/2021/2023 官方未釋出）

## 重點處理

- **編碼**：2002–2014 舊檔標籤為 Big5，程式自動偵測並以 big5 讀取；2015+ 自動偵測。
- **衍生變數沿用**：調查中心的 `SENGI`（父親省籍）/`TONDU`（統獨）/`T_Cidentity`/`SEX`/`EDU`/`AGE`/`PARTYID`
  跨年度編碼高度一致，直接沿用；代碼 3 = 大陸各省市人（外省）。
- **出生年**：各年原始題號不同（見 `build_excel.py` 的 `BIRTH_VAR`），逐年對應後換算西元＋世代；
  拒答（95/995…）與不合理年齡（<15 或 >105 歲）視為缺失。
- **特例**：2005 缺 `SENGI` 衍生變數 → 改用原始題 `Q40`；2002 標籤「大陸各省市」缺「人」→ 正規化。

## 重跑

```bash
.venv/bin/python build_excel.py      # 讀 raw/*.sav → 輸出 TNSS_harmonized.xlsx
.venv/bin/python inspect_derived.py  # 檢查各年衍生變數值標籤一致性
.venv/bin/python find_birthyear.py   # 檢查各年出生年題號
```

需要套件：`pyreadstat pandas openpyxl`（安裝見上方「取得原始資料並產生 xlsx」）

## 已知限制

- 族群以「父親省籍」為代理，非受訪者自陳；低估「外省母親／本省父親」家庭。
- 電訪對高齡與極年輕族群涵蓋率偏低；切世代×族群後兩端樣本可能個位數，解讀需謹慎。
- `taiwan_china_identity` 僅 2015 年後可用。
