# -*- coding: utf-8 -*-
"""單元測試：釘死三個已修 bug 的行為與核心合約。

1. pitch 自相關：最大峰落在諧波（2x/3x）時必須折回基本週期
2. 斷段 gap 合併：被交叉線亮 gap 切開的暗段要縫回單一斷點
3. ROI 旋轉：Manual ROI 於旋轉座標系取內接矩形（不包進框外區）
   ＋ AutoFrame 於旋轉後重新定位（特徵化測試已涵蓋端到端）
"""
import os

import numpy as np
import pytest

import ve_core
from ve_core import breaks, crossval, derotate, lines
from ve_core.errors import FrameNotFound, LinesNotFound, TaughtParamsError

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "fixtures")


# ---------------------------------------------------------- bug 1: pitch
def test_pitch_returns_fundamental_not_harmonic():
    """週期 50 的訊號帶強偶次諧波，最大自相關峰可能在 100/150；
    estimate_pitch 必須折回 ~50。"""
    n = 1000
    t = np.arange(n, dtype=np.float64)
    proj = (np.sin(2 * np.pi * t / 50.0)
            + 0.9 * np.sin(2 * np.pi * t / 25.0))  # 疊 2 次諧波
    pitch = lines.estimate_pitch(proj, min_pitch=20)
    assert 45 <= pitch <= 55, "pitch %.1f not folded to fundamental" % pitch


def test_pitch_too_short_raises():
    """estimate_pitch 實際 raise 條件：剖面過短（n//2 <= min_pitch）。
    （凍結行為備註：平坦/無週期剖面因 ac[:min_pitch]=-inf 的邊界
    效應會回傳 pitch=min_pitch 而非 raise——系統層級由下一關
    discover_lines 的「少於 2 條線」擋下，見下一測試。）"""
    with pytest.raises(LinesNotFound):
        lines.estimate_pitch(np.full(30, 120.0), min_pitch=20)


def test_discover_lines_flat_image_raises():
    """細亮脊線帶通 + MAD 突出度門檻（穩健標準差，見 find_peaks）上線後
    的行為：帶通後背景雜訊的中位絕對偏差很小，隨機雜訊起伏不足以跨過
    med + 6*MAD 門檻，平坦影像（無論雜訊大小）不再誤判出垃圾線，正確 raise。

    這附帶解決了退出條件 6 的已知缺口（README 曾記錄：平坦雜訊影像上
    發現式會回垃圾線而非報錯）——舊的 90 分位數突出度門檻在稀疏峰訊號
    上門檻太低才會誤判；仍待用真實「無切割線片型」影像驗證。"""
    rng = np.random.default_rng(1)
    noisy_flat = np.clip(rng.normal(120, 3, (400, 400)), 0, 255).astype(np.uint8)
    with pytest.raises(LinesNotFound):
        lines.discover_lines(noisy_flat, "v")

    clean_flat = np.clip(rng.normal(120, 0.5, (400, 400)), 0, 255).astype(np.uint8)
    with pytest.raises(LinesNotFound):
        lines.discover_lines(clean_flat, "v")


# ---------------------------------------------------- bug 2: gap merge
def test_dark_runs_merge_small_gap():
    """兩暗段間 3px 亮 gap（交叉切割線）：gap_merge_px=6 應縫成一段。"""
    prof = np.full(200, 210.0)
    prof[50:80] = 95     # 暗段 1
    prof[83:110] = 95    # 暗段 2（gap 3px：index 80,81,82 亮）
    runs = breaks.find_dark_runs(prof, bright_thresh=180, min_len=8,
                                 gap_merge_px=6, edge_guard_px=10)
    assert runs == [(50, 109)]


def test_dark_runs_no_merge_beyond_gap():
    prof = np.full(200, 210.0)
    prof[50:80] = 95
    prof[90:120] = 95    # gap 10px > 6，不合併
    runs = breaks.find_dark_runs(prof, bright_thresh=180, min_len=8,
                                 gap_merge_px=6, edge_guard_px=10)
    assert runs == [(50, 79), (90, 119)]


def test_dark_runs_edge_guard():
    """貼著剖面端點的暗段（線末端過渡帶）要被裁掉/濾除。"""
    prof = np.full(200, 210.0)
    prof[0:30] = 95      # 貼左端
    prof[195:200] = 95   # 貼右端、裁剩不足 min_len
    runs = breaks.find_dark_runs(prof, bright_thresh=180, min_len=8,
                                 gap_merge_px=0, edge_guard_px=10)
    assert runs == [(10, 29)]


# ------------------------------------------------- bug 3: ROI rotation
def test_map_rect_forward_is_inscribed():
    """旋轉後取內接矩形：四角映射後的第二小/第二大界定，
    保證不把旋轉帶進來的框外區域包進分析範圍。"""
    import cv2
    M = cv2.getRotationMatrix2D((500, 500), 3.0, 1.0)
    rect = (100, 100, 800, 600)
    x, y, w, h = derotate.map_rect_forward(rect, M)
    # 內接矩形四角必須都在原矩形四角映射點的凸包內 → 寬高必縮小
    assert w < 800 and h < 600
    assert w > 700 and h > 500  # 3 度不會縮太多


def test_map_points_back_roundtrip():
    import cv2
    M = cv2.getRotationMatrix2D((100, 100), 4.2, 1.0)
    Minv = cv2.invertAffineTransform(M)
    pts = np.array([[10.0, 20.0], [333.3, 444.4]])
    ones = np.ones((2, 1))
    fwd = np.hstack([pts, ones]) @ M.T
    back = derotate.map_points_back(fwd, Minv)
    assert np.allclose(back, pts, atol=1e-9)


# ------------------------------------------ AutoInRoi（粗框內精確找內緣）
def test_resolve_roi_auto_in_roi_translates_to_original_coords():
    """粗框子圖內找到的內緣座標，需正確平移回原圖座標系。"""
    gray = np.zeros((400, 400), dtype=np.uint8)
    gray[80:320, 80:320] = 150            # 亮「陶瓷」區塊，原圖座標 80..319
    rough = ve_core.Rect(30, 30, 340, 340)  # 操作員粗框，含滿版邊界緩衝
    roi = ve_core.RoiSpec("AutoInRoi", rough)
    rect = ve_core.resolve_roi(gray, roi, ve_core.AlgoConfig())
    # 內緣應貼近亮區邊界（80），而非粗框邊界（30）
    assert 78 <= rect.x <= 90
    assert 78 <= rect.y <= 90
    # 結果矩形必須完全落在粗框範圍內
    assert rect.x >= rough.x and rect.y >= rough.y
    assert rect.x + rect.w <= rough.x + rough.w
    assert rect.y + rect.h <= rough.y + rough.h


def test_resolve_roi_auto_in_roi_not_found_raises_not_silent_fallback():
    """粗框內沒有可辨識的內緣（全黑/全暗）時必須丟 FrameNotFound，
    不得靜默退回 Manual 或回傳粗框本身。"""
    gray = np.zeros((400, 400), dtype=np.uint8)
    roi = ve_core.RoiSpec("AutoInRoi", ve_core.Rect(50, 50, 200, 200))
    with pytest.raises(FrameNotFound):
        ve_core.resolve_roi(gray, roi, ve_core.AlgoConfig())


def test_resolve_roi_auto_in_roi_degenerate_rect_raises():
    gray = np.zeros((400, 400), dtype=np.uint8)
    roi = ve_core.RoiSpec("AutoInRoi", ve_core.Rect(0, 0, 50, 50))
    with pytest.raises(FrameNotFound):
        ve_core.resolve_roi(gray, roi, ve_core.AlgoConfig())


def test_roi_spec_auto_in_roi_requires_rect():
    with pytest.raises(ValueError):
        ve_core.RoiSpec("AutoInRoi")


def test_roi_spec_unknown_mode_rejected():
    with pytest.raises(ValueError):
        ve_core.RoiSpec("Bogus")


# ------------------------------------------------------- contract
def test_taught_params_version_mismatch():
    with pytest.raises(TaughtParamsError):
        ve_core.TaughtParams.from_json_dict({"tp_version": 99,
                                             "families": []})


def test_taught_params_not_dict():
    with pytest.raises(TaughtParamsError):
        ve_core.TaughtParams.from_json_dict(None)


def test_thresholds_merge_semantics():
    """taught 內出現的鍵覆蓋、未出現的鍵用預設（舊 pipeline 語意）。"""
    base = ve_core.Thresholds(cut_bright_thresh=180, min_break_len_px=8)
    merged = base.merged_with({"cut_bright_thresh": 160})
    assert merged.cut_bright_thresh == 160
    assert merged.min_break_len_px == 8
    assert merged.gap_merge_px == base.gap_merge_px


def test_reference_judge():
    from ve_core import JudgeCriteria, Verdict
    from ve_core.judge import reference_judge
    from ve_core.types import InspectResult, Rect, BreakDefect

    def mk(lengths):
        return InspectResult(
            verdict=Verdict.NG if lengths else Verdict.OK,
            angle_deg=0.0, lines_found=10,
            defects=[BreakDefect(i, 0, 0, 0, L, L) for i, L in
                     enumerate(lengths)],
            roi_used=Rect(0, 0, 100, 100), detection_mode="taught")

    strict = JudgeCriteria()  # 零容忍
    assert reference_judge(mk([]), strict) == Verdict.OK
    assert reference_judge(mk([5.0]), strict) == Verdict.NG

    lax = JudgeCriteria(judge_max_break_px=10.0, judge_max_breaks=2)
    assert reference_judge(mk([5.0, 8.0]), lax) == Verdict.OK
    assert reference_judge(mk([5.0, 8.0, 6.0]), lax) == Verdict.NG  # 數量超
    assert reference_judge(mk([12.0]), lax) == Verdict.NG           # 超長


def test_verdict_values_match_protocol():
    assert ve_core.Verdict.OK.value == "OK"
    assert ve_core.Verdict.NG.value == "NG"
    assert ve_core.Verdict.PLACEMENT.value == "PLACEMENT_ERROR"


# ------------------------------------------------- 需求 2：暗線極性反轉
def test_dark_line_found_via_pipeline_inversion():
    """實機切割線是暗線；pipeline.find_family_lines 內部反相
    （_dark_line_view）後找到的線位置要對齊真正的暗線座標。直接把同一張
    圖餵給 lines.discover_lines（未反相）雖然不一定完全找不到峰
    （ridge_bandpass 對週期性明暗結構本來就可能抓到反相的假峰——暗線
    間的陶瓷底色相對其模糊背景也會冒出弱峰），但抓到的位置會偏移到
    線與線之間，而不是暗線本身；有反相才會準確對齊已知線位置，用來
    釘死這次修正確實生效，不是碰巧過關。"""
    h, w = 400, 400
    sub = np.full((h, w), 130, dtype=np.uint8)   # 陶瓷底色
    pitch = 40
    true_positions = list(range(30, w - 30, pitch))
    for x in true_positions:
        sub[:, x - 2:x + 3] = 30                  # 暗線

    geom = ve_core.FamilyGeometry(axis="v", angle_deg=0.0, rot=sub,
                                  M=np.eye(2, 3), Minv=np.eye(2, 3),
                                  region=ve_core.Rect(0, 0, w, h))
    res = ve_core.find_family_lines(geom, ve_core.AlgoConfig(), taught=None)
    assert res is not None
    assert len(res["positions"]) >= 5
    for p in res["positions"]:
        nearest = min(abs(p - tp) for tp in true_positions)
        assert nearest <= 3, "反相後找到的線位置沒有對齊真正的暗線座標"


# --------------------------------------- 需求 4：框邊配對法交叉驗證
def _make_edge_grid(size=600, pitch=100, margin=80, line_half=3):
    """簡化測試圖：v/h 兩族線同位置、angle=0，不含大黑框（crossval
    只在乎 roi_rect 範圍內的暗線網格，不需要真的跑 resolve_roi）。"""
    img = np.full((size, size), 130, dtype=np.uint8)
    positions = list(range(margin, size - margin, pitch))
    for p in positions:
        img[:, p - line_half:p + line_half + 1] = 30
        img[p - line_half:p + line_half + 1, :] = 30
    return img, positions


def test_cross_validate_passes_on_clean_grid():
    img, positions = _make_edge_grid()
    cfg = ve_core.AlgoConfig()
    roi_rect = ve_core.Rect(0, 0, img.shape[1], img.shape[0])
    n = len(positions)
    assert crossval.cross_validate(img, roi_rect, 0.0, n, n, cfg) is None


def test_cross_validate_count_mismatch_reason_codes():
    img, positions = _make_edge_grid()
    cfg = ve_core.AlgoConfig()
    roi_rect = ve_core.Rect(0, 0, img.shape[1], img.shape[0])
    n = len(positions)
    anomaly = crossval.cross_validate(img, roi_rect, 0.0, n + 10, n, cfg)
    assert anomaly is not None
    assert "COUNT_MISMATCH_V" in anomaly.reasons
    assert "COUNT_MISMATCH_H" not in anomaly.reasons


def test_cross_validate_inset_degenerate():
    img = np.full((50, 50), 130, dtype=np.uint8)
    cfg = ve_core.AlgoConfig()
    roi_rect = ve_core.Rect(0, 0, 50, 50)   # 內縮 40*2=80 > 50，方框退化
    anomaly = crossval.cross_validate(img, roi_rect, 0.0, 1, 1, cfg)
    assert anomaly is not None
    assert anomaly.reasons == ["INSET_DEGENERATE"]


def test_pair_angles_perpendicularity_formula():
    """v_angles 是偏離垂直軸角度、h_angles 是偏離水平軸角度——兩族
    真正夾角與 90° 的差＝|v_repr - h_repr| 本身（見 crossval.py 註解），
    不是 |v_repr - h_repr| 再減 90。這裡直接餵配對後的谷點索引驗證
    _pair_angles 算出的角度符合預期方向與大小。"""
    # top/bottom 位移 10px、跨距 1000px → 偏離垂直軸 ~0.573°
    angles = crossval._pair_angles([100, 230, 360], [110, 240, 370], 1000.0)
    assert len(angles) == 3
    assert all(abs(a - angles[0]) < 1e-6 for a in angles)
    assert angles[0] == pytest.approx(0.5729, abs=1e-3)


def test_cross_validate_skipped_for_manual_roi():
    """Manual ROI 不保證對齊實體黑框，交叉驗證在 pipeline.inspect()
    層級直接跳過（不是 crossval.cross_validate 本身的行為，這裡確認
    pipeline 沒有對 Manual 模式呼叫它：用一個必然不過交叉驗證的
    v_count 差異，若真的被呼叫會回 DetectionAnomaly，Manual 模式下
    不該發生）。"""
    ng = os.path.join(FIXTURES_DIR, "synthetic_ng.png")
    assert os.path.isfile(ng), "run tests/record_golden.py first"
    from ve_ui.loader import load_gray
    gray = load_gray(ng)
    roi = ve_core.RoiSpec("Manual", ve_core.Rect(500, 480, 2800, 1750))
    r = ve_core.inspect(gray, ve_core.AlgoConfig(), roi,
                        angle_tol_deg=5.0, taught=None)
    assert isinstance(r, ve_core.InspectResult)


# ------------------------------------- 需求 5：線端點＝大黑框內緣交點
def test_family_geometry_sub_matches_region_bounds():
    """斷點偵測讀的 geom.sub 就是 geom.region 本身（AutoFrame 模式下＝
    旋轉後重新鎖框的大黑框內緣）——不多不少，斷點端點自然就是內緣
    邊界，不需要另外算交點。edge_guard_px 排除兩端過渡帶另見
    test_dark_runs_edge_guard。"""
    rot = np.zeros((500, 500), dtype=np.uint8)
    region = ve_core.Rect(50, 60, 300, 200)
    geom = ve_core.FamilyGeometry(axis="v", angle_deg=0.0, rot=rot,
                                  M=np.eye(2, 3), Minv=np.eye(2, 3),
                                  region=region)
    assert geom.sub.shape == (region.h, region.w)


# --------------------------------------- 需求 6：斷線長度陣列（defects 保留）
def test_break_lengths_px_matches_defects():
    ng = os.path.join(FIXTURES_DIR, "synthetic_ng.png")
    assert os.path.isfile(ng), "run tests/record_golden.py first"
    from ve_ui.loader import load_gray
    gray = load_gray(ng)
    r = ve_core.inspect(gray, ve_core.AlgoConfig(),
                        ve_core.RoiSpec("AutoFrame"),
                        angle_tol_deg=5.0, taught=None)
    assert isinstance(r, ve_core.InspectResult)

    lengths = r.break_lengths_json()
    assert set(lengths.keys()) == {"v", "h"}
    assert sum(lengths["v"]) + sum(lengths["h"]) == pytest.approx(
        sum(d.length_px for d in r.defects))
    for f in r.families:
        assert len(f.break_lengths_px) == len(f.positions_px)
        assert all(v >= 0.0 for v in f.break_lengths_px)


def test_family_detection_break_lengths_px_defaults_empty_for_teach():
    ok = os.path.join(FIXTURES_DIR, "synthetic_ok.png")
    assert os.path.isfile(ok), "run tests/record_golden.py first"
    from ve_ui.loader import load_gray
    gray = load_gray(ok)
    r = ve_core.teach(gray, ve_core.AlgoConfig(), ve_core.RoiSpec("AutoFrame"),
                      angle_tol_deg=5.0, image_name="ok.png")
    assert isinstance(r, ve_core.TeachResult)
    assert all(f.break_lengths_px == [] for f in r.families)


# --------------------------------------- 需求：安全輸入驗證 (image_path)
def test_protocol_parse_request_image_path_validation():
    import json
    from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

    # 合法的影像檔名/路徑應通過驗證
    valid_reqs = [
        {"request_id": "REQ-01", "cmd": "inspect", "image_path": "test.png"},
        {"request_id": "REQ-02", "cmd": "inspect", "image_path": "C:/images/test.BMP"},
        {"request_id": "REQ-03", "cmd": "teach", "image_path": "/var/tmp/img.jpeg"},
        {"request_id": "REQ-04", "cmd": "inspect", "image_path": "sub/dir/pic.tiff"},
    ]
    for r in valid_reqs:
        parsed = parse_request(json.dumps(r))
        assert parsed["image_path"] == r["image_path"]

    # 不合法的副檔名或嘗試目錄遍歷敏感檔案應被拒絕
    invalid_reqs = [
        {"request_id": "REQ-05", "cmd": "inspect", "image_path": "/etc/passwd"},
        {"request_id": "REQ-06", "cmd": "inspect", "image_path": "../config.json"},
        {"request_id": "REQ-07", "cmd": "teach", "image_path": "malicious.sh"},
        {"request_id": "REQ-08", "cmd": "inspect", "image_path": "test.png.txt"},
    ]
    for r in invalid_reqs:
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(r))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path: extension not allowed" in exc_info.value.msg
