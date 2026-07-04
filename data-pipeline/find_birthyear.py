"""找每年的原始出生年變數(民國年)，並檢查 2005 特殊結構。"""
import pyreadstat, glob, os, warnings
import numpy as np
warnings.filterwarnings("ignore")
RAW = os.path.join(os.path.dirname(__file__), "raw")


def read_full(path):
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


for path in sorted(glob.glob(f"{RAW}/*.sav")):
    yr = os.path.basename(path)[:4]
    df, meta, enc = read_full(path)
    labels = meta.column_names_to_labels
    # 找出生年題：label 含「出生」且非役男題
    cand = [(v, l) for v, l in labels.items()
            if l and "出生" in l and "役男" not in l]
    print(f"{yr} enc={enc}")
    for v, l in cand:
        col = df[v].dropna()
        # 判斷是否為民國年(值域約 20~100)
        try:
            vals = col[(col > 10) & (col < 200)]
            rng = f"min={col.min():.0f} max={col.max():.0f} n={len(col)}"
        except Exception:
            rng = "n/a"
        print(f"    {v} = {l[:30]}  ({rng})")
    if not cand:
        print("    (無『出生』題，變數清單前40個:)")
        print("    ", [n for n in meta.column_names][:40])
