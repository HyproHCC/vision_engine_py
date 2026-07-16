# -*- coding: utf-8 -*-
"""用 tests/stability_check.py 產出的 report（含 region_w/h、
positions_orig 兩個報表欄位）評估三項標準（ARCHITECTURE.md 第 9 節）：

  (a) pitch 穩定：同一族在各角度下 pitch 變異 < 1px
  (b) 線數 = region 尺寸 / pitch，容差 ±1 條（排除分析區隨角度縮放的
      幾何效應——region 越大理論線數越多，不是找線不穩）
  (c) 共同覆蓋區內，同一條實體線的原圖座標對齊 < 2px（以線數最多的
      角度為參考基準，逐條找最近鄰比對）

另外用「預期線位 ±pitch/4 內無峰」的定義找漏峰（用參考角度的線位
grid，檢查其他每個角度在該 grid 位置附近是否真的偵測到線）。

只做評估、不做任何回補/門檻調整——純粹讀 report、印出/寫出判讀結果。

用法：
  python tests/stability_analyze.py <report.json> [--out=analysis.json]
"""
import json
import statistics
import sys


def rep_pos(seg, axis):
    (x1, y1), (x2, y2) = seg
    return (x1 + x2) / 2.0 if axis == "v" else (y1 + y2) / 2.0


def region_dim(fam):
    return fam["region_w"] if fam["axis"] == "v" else fam["region_h"]


def load_family_rows(report, image, axis):
    out = {}
    for r in report["rows"]:
        if r["image"] != image or r["status"] not in ("OK", "NG"):
            continue
        fam = next((f for f in r.get("families", []) if f["axis"] == axis), None)
        if fam is None:
            continue
        out[r["target_angle"]] = fam
    return out


def evaluate_family(image: str, axis: str, by_angle: dict) -> dict:
    angles = sorted(by_angle.keys())
    pitches = [by_angle[a]["pitch_px"] for a in angles]

    # (a) pitch 穩定
    pitch_range = max(pitches) - min(pitches)
    pitch_pass = pitch_range < 1.0

    # (b) 線數 = region 尺寸 / pitch，容差 ±1
    count_checks = []
    for a in angles:
        fam = by_angle[a]
        expected = region_dim(fam) / fam["pitch_px"]
        diff = fam["line_count"] - expected
        count_checks.append({
            "target_angle": a, "line_count": fam["line_count"],
            "expected": round(expected, 2), "diff": round(diff, 2),
            "pass": abs(diff) <= 1.0 + 1e-9,
        })
    count_pass = all(c["pass"] for c in count_checks)

    # 參考角度＝該族線數最多的角度，其他角度都比對這個基準
    ref_angle = max(angles, key=lambda a: by_angle[a]["line_count"])
    ref_fam = by_angle[ref_angle]
    ref_pitch = ref_fam["pitch_px"]
    per_angle_positions = {
        a: sorted(rep_pos(seg, axis) for seg in by_angle[a]["positions_orig"])
        for a in angles
    }
    ref_positions = per_angle_positions[ref_angle]

    # 共同覆蓋區：每個角度線位範圍的交集
    lo = max(min(p) for p in per_angle_positions.values() if p)
    hi = min(max(p) for p in per_angle_positions.values() if p)

    # (c) 對齊：非參考角度、落在覆蓋區內的每條線，找最近的參考線比對距離
    align_diffs = []
    for a in angles:
        if a == ref_angle:
            continue
        for p in per_angle_positions[a]:
            if not (lo - 1e-6 <= p <= hi + 1e-6):
                continue
            nearest = min(ref_positions, key=lambda rp: abs(rp - p))
            if abs(nearest - p) > ref_pitch / 2.0:
                continue  # 配不到同一條線（視為額外/漏線，由下面漏峰檢查處理）
            align_diffs.append(abs(nearest - p))
    align_max = max(align_diffs) if align_diffs else None
    align_mean = statistics.mean(align_diffs) if align_diffs else None
    align_pass = (align_max is not None) and (align_max < 2.0)

    # 漏峰檢查：參考角度落在覆蓋區內的每個線位，其他角度在 ±pitch/4 內
    # 若沒有任何偵測到的線，記一筆漏峰
    ref_grid = [p for p in ref_positions if lo - 1e-6 <= p <= hi + 1e-6]
    half_win = ref_pitch / 4.0
    missing = []
    for a in angles:
        if a == ref_angle:
            continue
        actual = per_angle_positions[a]
        for gp in ref_grid:
            if not any(abs(ap - gp) <= half_win for ap in actual):
                missing.append({"target_angle": a, "expected_pos": round(gp, 2)})

    return {
        "image": image, "axis": axis,
        "pitch_values": [round(p, 2) for p in pitches],
        "pitch_range_px": round(pitch_range, 3),
        "pitch_pass": pitch_pass,
        "count_checks": count_checks,
        "count_pass": count_pass,
        "ref_angle": ref_angle,
        "overlap_range": [round(lo, 1), round(hi, 1)],
        "ref_grid_size": len(ref_grid),
        "align_max_px": round(align_max, 3) if align_max is not None else None,
        "align_mean_px": round(align_mean, 3) if align_mean is not None else None,
        "align_n_pairs": len(align_diffs),
        "align_pass": align_pass,
        "missing_peaks": missing,
        "missing_count": len(missing),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    report_path = sys.argv[1]
    out_path = None
    for arg in sys.argv[2:]:
        if arg.startswith("--out="):
            out_path = arg.split("=", 1)[1]

    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    images = sorted({r["image"] for r in report["rows"]})
    results = []
    for image in images:
        for axis in ("v", "h"):
            by_angle = load_family_rows(report, image, axis)
            if len(by_angle) < 2:
                continue
            res = evaluate_family(image, axis, by_angle)
            results.append(res)
            print("%-10s axis=%s pitch=%-24s range=%5.2fpx %-4s | "
                  "count(region/pitch +/-1)=%-4s | align(max=%s mean=%s n=%d)=%-4s | "
                  "missing=%d"
                  % (image, axis, res["pitch_values"], res["pitch_range_px"],
                     "PASS" if res["pitch_pass"] else "FAIL",
                     "PASS" if res["count_pass"] else "FAIL",
                     res["align_max_px"], res["align_mean_px"], res["align_n_pairs"],
                     "PASS" if res["align_pass"] else "FAIL",
                     res["missing_count"]))
            for c in res["count_checks"]:
                if not c["pass"]:
                    print("    COUNT FAIL target=%+5.2f line_count=%d expected=%.2f diff=%.2f"
                          % (c["target_angle"], c["line_count"], c["expected"], c["diff"]))
            for m in res["missing_peaks"][:20]:
                print("    MISSING target=%+5.2f expected_pos=%.1f"
                      % (m["target_angle"], m["expected_pos"]))
            if len(res["missing_peaks"]) > 20:
                print("    ... (%d more)" % (len(res["missing_peaks"]) - 20))

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=True)
        print("\nanalysis written:", out_path)


if __name__ == "__main__":
    main()
