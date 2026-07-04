"""
TNSS 跨年度欄位語意對齊 → 單一 Excel 活頁簿（一年一工作表，respondent-level）。

設計原則：
- 直接輸出人類可讀的中文標籤（而非代碼），讓下游 GAS / 前端無需再帶 codebook。
- 族群欄位以「父親省籍」(SENGI) 為準，代碼 3 = 大陸各省市人（外省）。
- X 軸用的出生年代由各年原始「出生年(民國)」題換算；此題各年題號不同（BIRTH_VAR）。
- 調查中心的衍生變數(SENGI/TONDU/T_Cidentity/SEX/EDU/AGE/PARTYID) 跨年高度一致，直接沿用。
- 缺欄位的年度該欄留空，但欄位結構所有年度一致。
"""
import os
import glob
import warnings
import pandas as pd
import pyreadstat

warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "raw")
OUT_XLSX = os.path.join(HERE, "TNSS_harmonized.xlsx")

# 各年原始「請問您是民國哪一年出生的？」題號（已逐年核實）
BIRTH_VAR = {
    "2002": "q35", "2004": "q36", "2005": "Q39", "2008": "Q39",
    "2011": "Q39", "2012": "Q37", "2013": "Q37", "2014": "Q37",
    "2015": "Q37", "2016": "Q36", "2017": "Q29", "2019": "Q30",
    "2020": "Q28", "2022": "Q29", "2024": "Q33", "2025": "Q30",
}

# 標準化欄位 -> 來源衍生變數名（大小寫不敏感，逐年可能大小寫不同）
DERIVED = {
    "father_ethnicity": "SENGI",          # 1本省客家 2本省閩南 3外省 4原住民 (5/6/7新住民) 9無反應
    "taiwan_china_identity": "T_CIDENTITY",  # 1臺灣人 2都是 3中國人 9無反應 (2015+)
    "unif_indep_stance": "TONDU",         # 1儘快統一…6儘快獨立 9無反應
    "party_id": "PARTYID",                # 1國民黨 2民進黨 …
    "gender": "SEX",                      # 1男 2女
    "education": "EDU",                   # 1小學以下…5大學以上
    "age_group": "AGE",                   # 1:20-29 … 5:60+
    "weight": "W",                        # 權值（無值標籤，直接取數值）
}

# 年度缺 SENGI 衍生變數時，改用原始「父親省籍」題（已逐年核實）
RAW_ETHNICITY_VAR = {"2005": "Q40"}


def normalize_ethnicity(label):
    """把逐年略有差異的族群標籤收斂成一致類別。"""
    if label is None or (isinstance(label, float)):
        return None
    s = str(label)
    if "大陸各省市" in s:          # 2002 作「大陸各省市」缺「人」
        return "大陸各省市人"
    if s in ("外國籍", "外籍人士", "外國人", "大陸新住民", "外國新住民"):
        return "新住民及其他"
    if ("無反應" in s) or ("拒答" in s) or ("不知道" in s) or ("其他" in s):
        return "無反應"
    return s  # 本省客家人 / 本省閩南人 / 原住民

OUTPUT_COLUMNS = [
    "survey_year", "birth_year_ad", "birth_cohort",
    "father_ethnicity", "taiwan_china_identity", "unif_indep_stance",
    "party_id", "gender", "education", "age_group", "weight",
]


def read_full(path):
    """讀整份資料，偵測 Big5 亂碼後退回 big5。"""
    last = None
    for enc in [None, "big5"]:
        try:
            df, meta = pyreadstat.read_sav(path, encoding=enc)
        except Exception:
            continue
        lab = (meta.column_names_to_labels.get("id")
               or meta.column_names_to_labels.get("ID") or "")
        if "樣" in lab or "編號" in lab:
            return df, meta, enc
        last = (df, meta, enc)
    return last


def ci_find(names, target):
    """大小寫不敏感找變數名。"""
    for n in names:
        if n.upper() == target.upper():
            return n
    return None


def code_to_label(series, value_labels):
    """用該年的值標籤把代碼轉中文；無標籤則保留原值。"""
    if not value_labels:
        return series
    return series.map(lambda v: value_labels.get(v, None))


def cohort_of(birth_ad):
    if pd.isna(birth_ad):
        return None
    decade = int(birth_ad // 10 * 10)
    return f"{decade}s"


def process_year(path):
    yr = os.path.basename(path)[:4]
    df, meta, enc = read_full(path)
    names = meta.column_names
    vlabels = meta.variable_value_labels  # var -> {code: label}

    out = pd.DataFrame()
    out["survey_year"] = [int(yr)] * len(df)

    # --- 出生年 → 西元 → 世代 ---
    bvar = BIRTH_VAR.get(yr)
    bcol = ci_find(names, bvar) if bvar else None
    if bcol is not None:
        raw = pd.to_numeric(df[bcol], errors="coerce")
        survey_minguo = int(yr) - 1911
        age = survey_minguo - raw
        # 995/999/95 等拒答代碼、以及不合理年齡 → 視為缺失
        valid = raw.notna() & (raw < 900) & (age >= 15) & (age <= 105)
        birth_ad = (raw + 1911).where(valid)
    else:
        birth_ad = pd.Series([None] * len(df))
    out["birth_year_ad"] = birth_ad.astype("Int64")
    out["birth_cohort"] = birth_ad.map(cohort_of)

    # --- 衍生類別/數值欄位 ---
    for canon, src in DERIVED.items():
        col = ci_find(names, src)
        # 族群缺衍生變數時退回原始題
        if col is None and canon == "father_ethnicity" and yr in RAW_ETHNICITY_VAR:
            col = ci_find(names, RAW_ETHNICITY_VAR[yr])
        if col is None:
            out[canon] = None
            continue
        if canon == "weight":
            out[canon] = pd.to_numeric(df[col], errors="coerce")
            continue
        labeled = code_to_label(df[col], vlabels.get(col))
        if canon == "father_ethnicity":
            labeled = labeled.map(normalize_ethnicity)
        out[canon] = labeled

    out = out[OUTPUT_COLUMNS]
    return yr, out, enc


def main():
    paths = sorted(glob.glob(f"{RAW}/*.sav"))
    summary = []
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        for path in paths:
            yr, out, enc = process_year(path)
            out.to_excel(writer, sheet_name=yr, index=False)
            # 覆蓋率統計
            cov = {c: int(out[c].notna().sum()) for c in OUTPUT_COLUMNS}
            cov["_n"] = len(out)
            cov["year"] = yr
            cov["enc"] = enc
            summary.append(cov)
            waisheng = (out["father_ethnicity"] == "大陸各省市人").sum()
            print(f"{yr}: n={len(out):>4}  外省={waisheng:>3}  "
                  f"有出生年={out['birth_year_ad'].notna().sum():>4}  enc={enc}")

        # meta 工作表：欄位說明
        meta_rows = [
            ["survey_year", "調查年度", "int"],
            ["birth_year_ad", "出生年（西元，由民國年換算，含清理）", "int"],
            ["birth_cohort", "出生年代（圖表 X 軸，如 1960s）", "字串"],
            ["father_ethnicity", "父親省籍（含『大陸各省市人』=外省）", "類別中文標籤"],
            ["taiwan_china_identity", "臺灣人/中國人/都是 認同（2015+）", "類別中文標籤"],
            ["unif_indep_stance", "統獨立場（6分類）", "類別中文標籤"],
            ["party_id", "政黨認同", "類別中文標籤"],
            ["gender", "性別", "類別中文標籤"],
            ["education", "教育程度", "類別中文標籤"],
            ["age_group", "年齡組（20-29…60+）", "類別中文標籤"],
            ["weight", "調查權值", "float"],
        ]
        pd.DataFrame(meta_rows, columns=["欄位", "說明", "型態"]).to_excel(
            writer, sheet_name="_meta", index=False)
        pd.DataFrame(summary).to_excel(writer, sheet_name="_coverage", index=False)

    print(f"\n輸出：{OUT_XLSX}")


if __name__ == "__main__":
    main()
