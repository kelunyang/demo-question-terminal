"""逐年掃描 .sav metadata，找出對應標準化欄位的候選變數。"""
import pyreadstat, glob, os, warnings, sys
warnings.filterwarnings("ignore")

RAW = os.path.join(os.path.dirname(__file__), "raw")

concepts = {
    "出生年": ["出生", "民國哪一年", "幾年出生", "生於"],
    "父親省籍": ["父親", "省籍", "本省", "閩南", "客家", "大陸各省"],
    "性別": ["性別"],
    "教育": ["學歷", "教育程度", "最高學歷", "教育"],
    "台中認同": ["臺灣人", "台灣人", "中國人"],
    "統獨": ["統一", "獨立", "維持現狀"],
    "政黨": ["政黨", "支持哪一個政黨", "偏向哪一個政黨"],
    "語言": ["使用語言", "訪問時使用"],
    "權重": ["權值", "權重", "加權"],
}


def load_meta(path):
    for enc in [None, "big5", "cp950", "utf-8"]:
        try:
            _, meta = pyreadstat.read_sav(path, metadataonly=True, encoding=enc)
            return meta, enc
        except Exception as e:
            last = e
    raise last


def main():
    for path in sorted(glob.glob(f"{RAW}/*.sav")):
        yr = os.path.basename(path)[:4]
        try:
            meta, enc = load_meta(path)
        except Exception as e:
            print(f"{yr} FAILED {e}")
            continue
        labels = meta.column_names_to_labels
        print("=" * 72)
        print(f"{yr}  n_vars={len(labels)}  enc={enc}")
        for concept, kws in concepts.items():
            hits = []
            for var, lab in labels.items():
                lab = lab or ""
                if any(k in lab for k in kws):
                    hits.append((var, lab))
            if hits:
                print(f"  [{concept}]")
                for var, lab in hits[:8]:
                    print(f"      {var} = {lab[:40]}")


if __name__ == "__main__":
    main()
