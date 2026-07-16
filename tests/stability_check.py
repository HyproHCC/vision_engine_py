# -*- coding: utf-8 -*-
"""±5° 找線穩定性驗證（Phase 1 退出條件 2，見 ARCHITECTURE.md 第 9 節）。

實圖數量通常不足以涵蓋機台允許的整個放置角容忍範圍，故對每張實圖疊加
一組 [-angle_tol, +angle_tol] 的合成旋轉（複用管線內部的
`derotate.rotate_keep_center`，BORDER_REPLICATE 不引入黑角，等同管線
自己去旋轉時的邊界處理），模擬「同一片料以不同角度放置」，逐一跑
`ve_core.inspect()`（發現式）檢查找線數 / pitch / 估角在整個容忍範圍內
是否穩定。

用法：
  python tests/stability_check.py <資料夾> [--angles=-5,-2.5,0,2.5,5] [--out=report.json]

不是 pytest 測試（依賴機台實圖，不在倉庫內）；獨立執行、印出統計摘要，
並把逐筆結果寫入 --out 指定的 JSON。

report 的 families[] 除了既有的 axis/pitch_px/line_count，另外兩個
純報表欄位（不影響偵測邏輯，供 tests/stability_analyze.py 用）：
  region_w / region_h  該族分析區（旋轉座標系）的寬高
  positions_orig       每條線映回原圖座標的兩端點 [[x1,y1],[x2,y2]]
"""
import glob
import json
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import ve_core  # noqa: E402
from ve_core import derotate as rot_mod  # noqa: E402
from ve_server.config import DEFAULTS  # noqa: E402

DEFAULT_ANGLES = [-5.0, -3.75, -2.5, -1.25, 0.0, 1.25, 2.5, 3.75, 5.0]


def load_gray(path: str) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise IOError("image load failed: %s" % path)
    return img


def run_one(gray: np.ndarray, cfg, angle_tol_deg: float) -> dict:
    """效果等同 ve_core.inspect()，改用分段 API（resolve_roi /
    estimate_angles / build_family_geometry / find_family_lines /
    detect_family_breaks，皆為 ve_core 既有函式，未複製或更動任何偵測
    /門檻邏輯）親自組裝，唯一目的是多保留每族的 FamilyGeometry，
    藉此用既有的 map_line_to_original 額外算出報表欄位
    （region_w/h、positions_orig）。"""
    roi = ve_core.RoiSpec("AutoFrame")
    t0 = time.perf_counter()

    def elapsed():
        return round((time.perf_counter() - t0) * 1000, 1)

    try:
        roi_rect = ve_core.resolve_roi(gray, roi, cfg)
        angles = ve_core.estimate_angles(gray, roi_rect, cfg)
        angle_deg = ve_core.placement_angle(angles)
        if abs(angle_deg) > float(angle_tol_deg):
            return {"status": "PLACEMENT_ERROR", "angle_deg": round(angle_deg, 3),
                    "lines_found": 0, "n_defects": 0, "families": [],
                    "elapsed_ms": elapsed()}

        thresholds = ve_core.Thresholds.from_config(cfg)
        defects_out = []
        fam_report = []
        lines_total = 0
        for ax in ve_core.FAMILY_AXES:
            geom = ve_core.build_family_geometry(gray, ax, angles[ax], roi,
                                                  roi_rect, cfg)
            res = ve_core.find_family_lines(geom, cfg, taught=None)
            if res is None:
                continue
            defects_out.extend(ve_core.detect_family_breaks(
                geom, res["positions"], thresholds, lines_total))
            lines_total += len(res["positions"])
            positions_orig = [ve_core.map_line_to_original(geom, p)
                              for p in res["positions"]]
            fam_report.append({
                "axis": ax,
                "pitch_px": res["pitch_px"],
                "line_count": len(res["positions"]),
                "region_w": geom.region.w,
                "region_h": geom.region.h,
                "positions_orig": [
                    [[round(p1[0], 2), round(p1[1], 2)],
                     [round(p2[0], 2), round(p2[1], 2)]]
                    for p1, p2 in positions_orig
                ],
            })
        if lines_total == 0:
            return {"status": "ERROR", "error": "no lines found on any axis",
                    "elapsed_ms": elapsed()}
        status = "NG" if defects_out else "OK"
        return {"status": status, "angle_deg": round(angle_deg, 3),
                "lines_found": lines_total, "n_defects": len(defects_out),
                "families": fam_report, "elapsed_ms": elapsed()}
    except ve_core.VeCoreError as e:
        return {"status": "ERROR", "error": str(e), "elapsed_ms": elapsed()}


def summarize(rows: list) -> dict:
    by_image = {}
    for row in rows:
        by_image.setdefault(row["image"], []).append(row)

    summary = {}
    for image, image_rows in by_image.items():
        ok_rows = [r for r in image_rows if r["status"] in ("OK", "NG")]
        lines_vals = [r["lines_found"] for r in ok_rows]
        errs = [abs(r["angle_deg"] - r["target_angle"]) for r in ok_rows]
        statuses = sorted({r["status"] for r in image_rows})
        summary[image] = {
            "n_runs": len(image_rows),
            "statuses": statuses,
            "lines_found_stable": len(set(lines_vals)) <= 1 if lines_vals else False,
            "lines_found_values": sorted(set(lines_vals)),
            "angle_recovery_max_err_deg": round(max(errs), 3) if errs else None,
            "angle_recovery_mean_err_deg": round(statistics.mean(errs), 3) if errs else None,
            "elapsed_ms_max": max(r["elapsed_ms"] for r in image_rows),
        }
    return summary


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    folder = sys.argv[1]
    angles = DEFAULT_ANGLES
    out_path = os.path.join(HERE, "stability_report.json")
    for arg in sys.argv[2:]:
        if arg.startswith("--angles="):
            angles = [float(x) for x in arg.split("=", 1)[1].split(",")]
        elif arg.startswith("--out="):
            out_path = arg.split("=", 1)[1]

    angle_tol_deg = 5.0  # 產線預設容忍值（PROTOCOL.md inspect.angle_tol_deg 預設）
    cfg = ve_core.AlgoConfig.from_dict(DEFAULTS["algo"])

    paths = sorted(glob.glob(os.path.join(folder, "*.png")))
    if not paths:
        print("no PNG found in", folder)
        sys.exit(1)

    rows = []
    for path in paths:
        gray = load_gray(path)
        name = os.path.basename(path)

        # 先量原圖自身的擺放角，合成旋轉前扣掉，讓「目標角度」直接對應
        # 估角結果（避免原圖本身就有殘留角度時，邊界目標如 -5° 疊加後
        # 實際估角超過容忍值，誤觸 PLACEMENT_ERROR）。
        base_res = run_one(gray, cfg, angle_tol_deg)
        baseline_angle = (base_res.get("angle_deg", 0.0)
                          if base_res["status"] in ("OK", "NG") else 0.0)

        for target in angles:
            if target == 0.0:
                res, injected = dict(base_res), 0.0
            else:
                injected = round(baseline_angle - target, 4)
                test_img = rot_mod.rotate_keep_center(gray, injected)[0]
                res = run_one(test_img, cfg, angle_tol_deg)
            res.update(image=name, injected_angle=injected, target_angle=target)
            rows.append(res)
            print("%-8s target=%+5.2f (inj=%+6.2f) -> status=%-15s angle=%7s lines=%-4s defects=%-3s %6.1fms"
                  % (name, target, injected, res["status"], res.get("angle_deg", "n/a"),
                     res.get("lines_found", "n/a"), res.get("n_defects", "n/a"),
                     res["elapsed_ms"]))

    summary = summarize(rows)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"angles": angles, "rows": rows, "summary": summary},
                  f, indent=2, ensure_ascii=True)

    print("\n=== summary ===")
    for image, s in summary.items():
        print("%-10s runs=%-3d statuses=%-20s lines_stable=%-5s lines=%-10s "
              "angle_err(max/mean)=%s/%s deg  max=%.1fms"
              % (image, s["n_runs"], s["statuses"], s["lines_found_stable"],
                 s["lines_found_values"], s["angle_recovery_max_err_deg"],
                 s["angle_recovery_mean_err_deg"], s["elapsed_ms_max"]))
    print("\nreport written:", out_path)


if __name__ == "__main__":
    main()
