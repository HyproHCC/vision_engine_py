# -*- coding: utf-8 -*-
"""InspectionSession（分段快取）測試 —— 無 Qt 相依。

1. 快取正確性：門檻變動後結果 = 全新 session 冷跑同參數的結果
2. 快取有效性：門檻變動只重算 breaks 階段（無 angle/geom 重算），
   且耗時 << 冷跑
3. teach 模式輸出與 ve_server.engine 的 teach 一致（同一份 ve_core）
4. 放置異常路徑
"""
import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ve_core
from ve_ui.loader import load_gray
from ve_ui.session import InspectionSession

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_NG = os.path.join(HERE, "fixtures", "synthetic_ng.png")
IMG_OK = os.path.join(HERE, "fixtures", "synthetic_ok.png")


@pytest.fixture(scope="module")
def gray_ng():
    return load_gray(IMG_NG)


@pytest.fixture(scope="module")
def gray_ok():
    return load_gray(IMG_OK)


def _defect_tuples(r):
    return sorted((d.line_id, d.x1, d.y1, d.x2, d.y2, d.length_px)
                  for d in r.defects)


def test_cold_run_finds_ground_truth(gray_ng):
    s = InspectionSession()
    s.set_image(gray_ng, IMG_NG)
    r = s.run()
    assert r.ok and r.engine_status == "NG"
    assert len(r.defects) == 2
    assert r.stage_ms.keys() >= {"roi", "angle", "geom", "lines", "breaks"}


def test_threshold_change_only_recomputes_breaks(gray_ng):
    s = InspectionSession()
    s.set_image(gray_ng, IMG_NG)
    r1 = s.run()
    cold_ms = r1.total_ms

    # 動門檻滑桿 → 只有 breaks 重算
    s.update_params("thresholds", cut_bright_thresh=150.0)
    r2 = s.run()
    assert set(r2.stage_ms.keys()) == {"breaks"}, r2.stage_ms
    assert r2.total_ms < cold_ms / 5, \
        "threshold rerun %.0fms not << cold %.0fms" % (r2.total_ms, cold_ms)

    # 快取正確性：等於冷跑同參數
    s2 = InspectionSession()
    s2.update_params("thresholds", cut_bright_thresh=150.0)
    s2.set_image(gray_ng, IMG_NG)
    r_cold = s2.run()
    assert _defect_tuples(r2) == _defect_tuples(r_cold)
    assert r2.engine_status == r_cold.engine_status


def test_lines_param_recomputes_lines_and_breaks_only(gray_ng):
    s = InspectionSession()
    s.set_image(gray_ng, IMG_NG)
    s.run()
    s.update_params("lines", peak_min_dist_ratio=0.5)
    r = s.run()
    assert set(r.stage_ms.keys()) == {"lines", "breaks"}, r.stage_ms


def test_angle_param_invalidates_downstream(gray_ng):
    s = InspectionSession()
    s.set_image(gray_ng, IMG_NG)
    s.run()
    s.update_params("angle", angle_fine_step=0.1)
    r = s.run()
    assert set(r.stage_ms.keys()) == {"angle", "geom", "lines", "breaks"}


def test_teach_matches_server_engine(gray_ok):
    logging.disable(logging.CRITICAL)
    s = InspectionSession()
    s.set_image(gray_ok, IMG_OK)
    s.set_mode("teach")
    r = s.run()
    assert r.ok and r.taught is not None
    ui_tp = r.taught.to_json_dict()

    from ve_server.engine import Engine
    from ve_server.config import DEFAULTS
    eng = Engine(DEFAULTS["algo"], "/tmp/ng_sess", logging.getLogger("t"))
    srv_tp = eng.teach({"roi_mode": "AutoFrame", "angle_tol_deg": 5.0,
                        "image_path": IMG_OK})["taught_params"]
    for tp in (ui_tp, srv_tp):
        tp["reference"].pop("taught_at")
        tp["reference"].pop("image")
    assert ui_tp == srv_tp, "調機工具與生產 server 的教導結果不一致"


def test_teach_then_taught_inspect_roundtrip(gray_ok, gray_ng):
    s = InspectionSession()
    s.set_image(gray_ok, IMG_OK)
    s.set_mode("teach")
    tp = s.run().taught
    assert tp is not None

    s.set_taught(tp)
    s.set_mode("taught")
    s.set_image(gray_ng, IMG_NG)
    r = s.run()
    assert r.ok and r.engine_status == "NG"
    assert len(r.defects) == 2
    assert all(f.mode == "taught" for f in r.families)


def test_placement_path(gray_ng):
    s = InspectionSession()
    s.set_image(gray_ng, IMG_NG)
    s.set_angle_tol(1.0)          # 合成圖旋轉 1.5° > 1.0°
    r = s.run()
    assert r.ok and r.placement
    assert r.verdict == "Placement"
    # 放寬 tol 後可從 GEOM 續跑（角度快取仍有效）
    s.set_angle_tol(5.0)
    r2 = s.run()
    assert not r2.placement and r2.engine_status == "NG"
    assert "angle" not in r2.stage_ms, "angle 不應重算"


def test_judge_criteria_applied(gray_ng):
    s = InspectionSession()
    s.set_image(gray_ng, IMG_NG)
    r = s.run()
    assert r.verdict == "NG"      # 零容忍
    # 放寬到容忍 2 個 150px 斷點 → 參考 verdict 轉 OK（engine 仍 NG）
    s.update_judge(judge_max_break_px=150.0, judge_max_breaks=2)
    r2 = s.run()
    assert r2.engine_status == "NG"
    assert r2.verdict == "OK"
