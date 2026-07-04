"""用正確編碼逐年檢查調查中心衍生變數的數值標籤是否跨年一致。"""
import pyreadstat, glob, os, warnings
warnings.filterwarnings("ignore")

RAW = os.path.join(os.path.dirname(__file__), "raw")


def read_meta(path):
    """舊檔(2002-2014)標籤為 Big5；2015+ 通常 auto 即可。偵測亂碼後退回 big5。"""
    best = None
    for enc in [None, "big5"]:
        try:
            _, meta = pyreadstat.read_sav(path, metadataonly=True, encoding=enc)
        except Exception:
            continue
        # 用 id 變數的標籤判斷編碼是否正確（應含 CJK "樣本"）
        lab = (meta.column_names_to_labels.get("id")
               or meta.column_names_to_labels.get("ID") or "")
        if "樣" in lab or "編號" in lab:
            return meta, enc
        best = (meta, enc)
    return best  # 退而求其次


def ci_get(d, name):
    """case-insensitive 取值標籤 dict。"""
    for k, v in d.items():
        if k.upper() == name.upper():
            return k, v
    return None, None


TARGETS = ["SENGI", "SENGI7", "TONDU", "T_CIDENTITY", "SEX", "EDU", "AGE",
           "PARTYID", "PARTY", "W"]

for path in sorted(glob.glob(f"{RAW}/*.sav")):
    yr = os.path.basename(path)[:4]
    meta, enc = read_meta(path)
    vl = meta.variable_value_labels  # var -> {code: label}
    print("=" * 74)
    print(f"{yr}  enc={enc}")
    for t in TARGETS:
        realname, codes = ci_get(vl, t)
        if realname is None:
            # 變數存在但無值標籤？
            if any(n.upper() == t for n in meta.column_names):
                print(f"  {t}: (存在，無值標籤)")
            continue
        # 精簡顯示
        items = list(codes.items())[:9]
        s = "  ".join(f"{k}={v}" for k, v in items)
        print(f"  {realname}: {s}")
