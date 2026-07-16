# -*- coding: utf-8 -*-
"""特徵化測試：ve_core（經 ve_server.engine）輸出必須與重構前
的舊 pipeline golden 完全一致。

golden 由 tests/record_golden.py 以舊程式碼錄製（重構時一次），
重構後任何數值行為差異都會在這裡爆開。
比對前正規化：reference.taught_at（時間戳）與 ng_image_path
（時間戳/流水號路徑，只比有無）。
"""
import json
import logging
import os

import cv2
import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "golden", "pipeline_golden.json")
IMG_NG = os.path.join(HERE, "fixtures", "synthetic_ng.png")
IMG_OK = os.path.join(HERE, "fixtures", "synthetic_ok.png")

log = logging.getLogger("test")


def _normalize(resp: dict) -> dict:
    r = json.loads(json.dumps(resp))  # deep copy + tuple->list
    if "ng_image_path" in r:
        r["ng_image_path"] = bool(r["ng_image_path"])
    tp = r.get("taught_params")
    if isinstance(tp, dict) and isinstance(tp.get("reference"), dict):
        tp["reference"].pop("taught_at", None)
    return r


@pytest.fixture(scope="module")
def golden():
    with open(GOLDEN, encoding="utf-8") as f:
        g = json.load(f)
    for k, v in g.items():
        if isinstance(v, dict):
            g[k] = _normalize(v)
    return g


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    from ve_server.engine import Engine
    from ve_server.config import DEFAULTS
    ng_dir = str(tmp_path_factory.mktemp("ng"))
    return Engine(DEFAULTS["algo"], ng_dir, log)


@pytest.fixture(scope="module")
def images():
    assert os.path.isfile(IMG_NG) and os.path.isfile(IMG_OK), \
        "run tests/record_golden.py first to generate fixtures"
    return IMG_NG, IMG_OK


BASE = {"roi_mode": "AutoFrame", "angle_tol_deg": 5.0}


@pytest.fixture(scope="module")
def teach_ok(engine, images):
    _, ok = images
    return engine.teach({**BASE, "image_path": ok})


def test_teach_matches_golden(golden, teach_ok):
    assert _normalize(teach_ok) == golden["teach_ok"]


def test_inspect_discovery_ng(golden, engine, images):
    ng, _ = images
    r = engine.inspect({**BASE, "image_path": ng, "param_source": "None"})
    assert _normalize(r) == golden["inspect_discovery_ng"]


def test_inspect_taught_ng(golden, engine, images, teach_ok):
    ng, _ = images
    r = engine.inspect({**BASE, "image_path": ng, "param_source": "Taught",
                        "taught_params": teach_ok["taught_params"]})
    assert _normalize(r) == golden["inspect_taught_ng"]


def test_inspect_taught_ok(golden, engine, images, teach_ok):
    _, ok = images
    r = engine.inspect({**BASE, "image_path": ok, "param_source": "Taught",
                        "taught_params": teach_ok["taught_params"]})
    assert _normalize(r) == golden["inspect_taught_ok"]


def test_inspect_manual_roi(golden, engine, images):
    ng, _ = images
    r = engine.inspect({"roi_mode": "Manual",
                        "roi_rect": {"left": 500, "top": 480,
                                     "right": 3300, "bottom": 2230},
                        "angle_tol_deg": 5.0,
                        "image_path": ng, "param_source": "None"})
    assert _normalize(r) == golden["inspect_manual_roi_ng"]


def test_inspect_placement(golden, engine, images):
    ng, _ = images
    r = engine.inspect({**BASE, "image_path": ng, "param_source": "None",
                        "angle_tol_deg": 1.0})
    assert _normalize(r) == golden["inspect_placement"]


def test_defects_match_ground_truth(golden, engine, images):
    """斷點座標對照合成影像 ground truth（獨立於 golden 的絕對檢核）。"""
    ng, _ = images
    r = engine.inspect({**BASE, "image_path": ng, "param_source": "None"})
    assert r["status"] == "NG"
    assert len(r["defects"]) == len(golden["ground_truth_breaks"])


def test_taught_params_wire_format_frozen(teach_ok):
    """退出條件 7：taught_params JSON 鍵集合凍結（生產格式）。"""
    tp = teach_ok["taught_params"]
    assert set(tp.keys()) == {"tp_version", "families", "thresholds",
                              "reference"}
    for f in tp["families"]:
        assert set(f.keys()) == {"axis", "angle_deg", "pitch_px",
                                 "line_count", "positions_px"}
    assert set(tp["thresholds"].keys()) >= {"cut_bright_thresh",
                                            "min_break_len_px",
                                            "band_halfwidth_px"}
    assert set(tp["reference"].keys()) == {"taught_at", "image"}
    # 序列化必須可 ASCII（協定 ensure_ascii）
    json.dumps(tp, ensure_ascii=True)


def test_roundtrip_taught_params(teach_ok):
    """dataclass <-> JSON 往返不失真（LabVIEW 原樣搬運的前提）。"""
    import ve_core
    tp = ve_core.TaughtParams.from_json_dict(teach_ok["taught_params"])
    d = tp.to_json_dict()
    d["reference"].pop("taught_at")
    ref = json.loads(json.dumps(teach_ok["taught_params"]))
    ref["reference"].pop("taught_at")
    assert d == ref
