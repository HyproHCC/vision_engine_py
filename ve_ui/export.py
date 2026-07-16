# -*- coding: utf-8 -*-
"""結果與參數匯出（JSON / CSV），供離線統計與門檻分析。

CSV 一律 utf-8-sig（帶 BOM）：CP950 地區的 Excel 直接雙擊開啟
不會亂碼。JSON 一律 utf-8（分析腳本用）。
"""
import csv
import datetime
import json

import ve_core


def _meta(cfg, thresholds, judge, roi, angle_tol, mode):
    return {
        "exported_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "ve_core_version": ve_core.__version__,
        "mode": mode,
        "roi_mode": roi.mode,
        "roi_rect": roi.rect.to_json_dict() if roi.rect else None,
        "angle_tol_deg": angle_tol,
        "algo_config": cfg.to_dict(),
        "thresholds": thresholds.to_json_dict(),
        "judge": {"judge_max_break_px": judge.judge_max_break_px,
                  "judge_max_breaks": judge.judge_max_breaks},
    }


def export_single_json(path, result, image_path, cfg, thresholds, judge,
                       roi, angle_tol, mode):
    """單張檢測結果 + 完整參數（可重現該次結果）。"""
    doc = {"meta": _meta(cfg, thresholds, judge, roi, angle_tol, mode),
           "image": image_path,
           "result": {
               "ok": result.ok, "message": result.message,
               "engine_status": result.engine_status,
               "verdict": result.verdict,
               "angle_deg": result.angle_deg,
               "roi_used": (result.roi_rect.to_json_dict()
                            if result.roi_rect else None),
               "families": [{"axis": f.axis, "angle_deg": f.angle_deg,
                             "pitch_px": f.pitch_px,
                             "line_count": f.line_count, "mode": f.mode}
                            for f in result.families],
               "defects": [d.to_json_dict() | {"axis": d.axis}
                           for d in result.defects],
               "stage_ms": result.stage_ms,
               "total_ms": result.total_ms}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def export_batch_json(path, rows, defect_rows, cfg, thresholds, judge,
                      roi, angle_tol, mode):
    doc = {"meta": _meta(cfg, thresholds, judge, roi, angle_tol, mode),
           "images": rows, "defects": defect_rows}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def export_batch_csv(path, rows):
    cols = ("image", "status", "verdict", "angle_deg", "lines_found",
            "n_defects", "max_break_px", "elapsed_ms", "error", "path")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def export_defects_csv(path, defect_rows):
    cols = ("image", "line_id", "axis", "x1", "y1", "x2", "y2", "length_px")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(defect_rows)


def save_taught_json(path, taught: "ve_core.TaughtParams"):
    """教導結果存檔 —— 就是生產凍結格式（PROTOCOL.md 第 7 節）。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(taught.to_json_dict(), f, ensure_ascii=True, indent=2)


def load_taught_json(path) -> "ve_core.TaughtParams":
    with open(path, "r", encoding="utf-8") as f:
        return ve_core.TaughtParams.from_json_dict(json.load(f))
