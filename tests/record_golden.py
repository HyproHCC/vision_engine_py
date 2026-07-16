# -*- coding: utf-8 -*-
"""用 ve_server.engine.Engine 錄製 golden 輸出（tests/make_test_image.py
產生的合成暗線圖）。ve_core 的特徵化測試以此為基準比對。

只在演算法行為**刻意**改變時重錄（見 ARCHITECTURE.md 7 節），重錄前
先確認差異是預期的。

用法： python tests/record_golden.py
"""
import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import cv2  # noqa: E402

from make_test_image import build  # noqa: E402

GOLDEN_DIR = os.path.join(HERE, "golden")
IMG_DIR = os.path.join(HERE, "fixtures")


def imwrite_unicode(path: str, img) -> None:
    """cv2.imwrite 在非 ASCII 路徑下靜默失敗（回傳 False、不丟例外，
    與 ARCHITECTURE.md 記錄的 cv2.imread CP950 地雷同一類）；改用
    cv2.imencode + Python 內建檔案 I/O 繞路（比照 ve_ui/loader.py 讀圖
    的解法；numpy 的 tofile 一樣走 C 層路徑，不保證安全，故用 open()）。"""
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise IOError("cv2.imencode failed: %s" % path)
    with open(path, "wb") as f:
        f.write(buf.tobytes())


def main():
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("golden")

    ng_img, gt = build(with_breaks=True)
    ok_img, _ = build(with_breaks=False)
    ng_path = os.path.join(IMG_DIR, "synthetic_ng.png")
    ok_path = os.path.join(IMG_DIR, "synthetic_ok.png")
    imwrite_unicode(ng_path, ng_img)
    imwrite_unicode(ok_path, ok_img)

    base = {"roi_mode": "AutoFrame", "angle_tol_deg": 5.0}
    ng_dir = "/tmp/golden_ng"

    from ve_server.engine import Engine
    from ve_server.config import DEFAULTS
    eng = Engine(DEFAULTS["algo"], ng_dir, log)
    run_teach = lambda req: eng.teach(req)
    run_inspect = lambda req: eng.inspect(req)

    out = {}
    out["ground_truth_breaks"] = [list(g) for g in gt]

    tr = run_teach({**base, "image_path": ok_path})
    out["teach_ok"] = tr

    out["inspect_discovery_ng"] = run_inspect(
        {**base, "image_path": ng_path, "param_source": "None"})

    out["inspect_taught_ng"] = run_inspect(
        {**base, "image_path": ng_path, "param_source": "Taught",
         "taught_params": tr["taught_params"]})

    out["inspect_taught_ok"] = run_inspect(
        {**base, "image_path": ok_path, "param_source": "Taught",
         "taught_params": tr["taught_params"]})

    # manual ROI 路徑也要鎖（map_rect_forward 內接矩形行為）
    out["inspect_manual_roi_ng"] = run_inspect(
        {"roi_mode": "Manual",
         "roi_rect": {"left": 500, "top": 480, "right": 3300, "bottom": 2230},
         "angle_tol_deg": 5.0,
         "image_path": ng_path, "param_source": "None"})

    # placement error 路徑（tol 縮小到 1 度使 1.5 度旋轉超限）
    out["inspect_placement"] = run_inspect(
        {**base, "image_path": ng_path, "param_source": "None",
         "angle_tol_deg": 1.0})

    # ng_image_path 帶時間戳/流水號，不可比對 → 只記錄有無
    for k in out:
        if isinstance(out[k], dict) and "ng_image_path" in out[k]:
            out[k]["ng_image_path"] = bool(out[k]["ng_image_path"])

    dst = os.path.join(GOLDEN_DIR, "pipeline_golden.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=True, sort_keys=True)
    print("golden written:", dst)
    for k, v in out.items():
        if isinstance(v, dict):
            print("  %-24s status=%-16s defects=%s" % (
                k, v.get("status"), len(v.get("defects", []))))


if __name__ == "__main__":
    main()
