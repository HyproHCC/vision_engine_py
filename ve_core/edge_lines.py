# -*- coding: utf-8 -*-
"""框邊配對法——主要找線方法（Ctype 片型，暗線）。

跟 crossval.py 的「次要驗證」不同，這裡是**主要**找線＋斷點偵測路徑，
只在 `AlgoConfig.line_find_method == "edge_pairing"` 時由 pipeline.inspect()
呼叫（teach() 不支援，taught_params 的 positions_px 語意是為投影法的
per-family 幾何設計的，跟這裡「單一整張旋轉、frame 相對」的座標模型
不吻合）。

流程：
1. 用既有 estimate_angles 估出的 angle_deg 把整張圖轉正
   （derotate.rotate_keep_center，跟 build_family_geometry 手法一致）。
2. 轉正後在旋轉座標系重跑 find_inner_roi 找大黑框內緣（region）。
3. 內緣往內縮 EDGE_PAIR_INSET_PX 到內側大亮帶（清楚無晶粒干擾，
   實測 ng/piece_001.png 校準，見 commit 說明）。
4. 沿小方框四邊取剖面找谷點（重用 crossval._edge_profile/_find_valleys，
   已經是這個方法的核心邏輯）。
5. 兩側谷點數只差 1（斷點恰好卡在方框邊界漏偵測）用 pitch 規律內插
   補回；差 2 個以上不強行湊，讓下一步的硬性檢查照實回報。
6. 兩側谷點數還是對不上 → DetectionAnomaly（這裡沒有 crossval 那種
   ±1 容差——主要找線法配對不出來就是真的沒辦法，不是驗證用的軟檢查）。
7. 對側谷點依序配對成線，兩點的直線方程式跟 region 對應邊求交點，
   得到線的真正端點（旋轉座標系）。
8. 沿端點取任意角度 profile（_line_profile，band 平均），反相後重用
   breaks.find_dark_runs 判斷斷線（Ctype 是亮街道中的細暗線：斷點=
   曝露街道=亮，反相後變暗，交給既有的「暗=斷」判準，不改該函式）。
9. 座標一律映回原圖（derotate.map_points_back）。

新參數先集中寫死成常數（本檔頂部），收斂後再整理進 AlgoConfig 面板，
見 ARCHITECTURE.md 第 9 節待辦。
"""
import logging
import math
from typing import Tuple, Union

import numpy as np

from . import breaks as breaks_mod
from . import derotate as rot_mod
from . import frame as frame_mod
from .crossval import _edge_profile, _find_valleys
from .errors import FrameNotFound
from .lines import DEFAULT_MIN_PITCH_PX
from .types import AlgoConfig, BreakDefect, DetectionAnomaly, FamilyDetection, Rect

logger = logging.getLogger("ve_core")

# ---- 先寫死的常數（待收斂後整理進 AlgoConfig，見 ARCHITECTURE.md 9 節）----
EDGE_PAIR_INSET_PX = 250        # 黑框內緣到內側大亮帶的內縮距離，實測校準
EDGE_PAIR_PROFILE_BAND_PX = 4   # 剖面鄰域平均半寬（規格 3~5px）
EDGE_PAIR_CUT_THRESH = 150      # 亮/暗分界，實測校準
EDGE_PAIR_MIN_BREAK_PX = 3      # 連續 px 視為斷線（規格明訂）
EDGE_PAIR_GAP_MERGE_PX = 6      # 沿用 Thresholds 既有預設
EDGE_PAIR_EDGE_GUARD_PX = 5


def _complete_missing_valley(short: list, long: list) -> list:
    """short 比 long 少一個谷點，多半是斷點恰好落在方框邊界上漏偵測。
    用 long 的間距中位數當 pitch，在 short 裡找哪個間隙異常寬（≈2x
    pitch 以上），從那個間隙的中點內插補一個。條件不滿足（差距不是
    剛好 1 個、long 太短測不出可靠 pitch、short 裡沒有明顯異常寬的
    間隙）一律原樣傳回，不強行猜——讓上游硬性 count 檢查照實回報。"""
    if len(long) - len(short) != 1 or len(long) < 3:
        return short
    pitch = float(np.median(np.diff(long)))
    if pitch <= 0:
        return short
    if len(short) < 2:
        return short
    diffs = np.diff(short)
    gap_i = int(np.argmax(diffs))
    if diffs[gap_i] < 1.5 * pitch:
        return short
    insert_pos = (short[gap_i] + short[gap_i + 1]) / 2.0
    result = list(short)
    result.insert(gap_i + 1, insert_pos)
    logger.debug("edge_pairing: 補漏谷 pos=%.1f（間隙 %.1f，pitch=%.1f）",
                insert_pos, diffs[gap_i], pitch)
    return result


def _line_frame_intersection(p1: tuple, p2: tuple, region: Rect,
                             axis: str) -> tuple:
    """(p1,p2) 是小方框上兩個對側谷點（旋轉座標系）。求通過這兩點的
    直線與 region（大黑框內緣）對應邊的交點，得到線的真正端點。"""
    (x1, y1), (x2, y2) = p1, p2
    if axis == "v":
        y_top, y_bot = float(region.y), float(region.y + region.h - 1)
        t0 = (y_top - y1) / (y2 - y1)
        t1 = (y_bot - y1) / (y2 - y1)
        xa = x1 + (x2 - x1) * t0
        xb = x1 + (x2 - x1) * t1
        return (xa, y_top), (xb, y_bot)
    x_left, x_right = float(region.x), float(region.x + region.w - 1)
    t0 = (x_left - x1) / (x2 - x1)
    t1 = (x_right - x1) / (x2 - x1)
    ya = y1 + (y2 - y1) * t0
    yb = y1 + (y2 - y1) * t1
    return (x_left, ya), (x_right, yb)


def _line_profile(rot_gray: np.ndarray, p1: tuple, p2: tuple,
                  band_px: int) -> np.ndarray:
    """沿任意角度線段從 p1 到 p2 取剖面，每點＝垂直線段方向 ±band_px
    鄰域平均（profile.band_profile 只處理軸對齊，這裡是通用版本）。"""
    x1, y1 = p1
    x2, y2 = p2
    length = int(round(math.hypot(x2 - x1, y2 - y1)))
    if length < 2:
        return np.zeros(0, dtype=np.float64)
    h, w = rot_gray.shape
    t = np.arange(length, dtype=np.float64)
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    cx = x1 + dx * t
    cy = y1 + dy * t
    nx, ny = -dy, dx
    ks = np.arange(-band_px, band_px + 1, dtype=np.float64)
    xs = np.round(cx[:, None] + nx * ks[None, :]).astype(np.int64)
    ys = np.round(cy[:, None] + ny * ks[None, :]).astype(np.int64)
    valid = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
    xs_c = np.clip(xs, 0, w - 1)
    ys_c = np.clip(ys, 0, h - 1)
    vals = rot_gray[ys_c, xs_c].astype(np.float64)
    vals[~valid] = np.nan
    with np.errstate(invalid="ignore"):
        prof = np.nanmean(vals, axis=1)
    return np.nan_to_num(prof, nan=0.0)


def _est_pitch(sorted_positions: list) -> float:
    if len(sorted_positions) < 2:
        return 0.0
    return float(np.median(np.diff(sorted_positions)))


def inspect_edge_pairing(
        gray: np.ndarray, roi_rect: Rect, angle_deg: float, cfg: AlgoConfig
) -> Union[DetectionAnomaly, Tuple[list, list, int]]:
    """框邊配對法主要找線＋斷點。成功回傳
    (fam_details: list[FamilyDetection], defects: list[BreakDefect],
     lines_total: int)；配對不出來回傳 DetectionAnomaly。
    """
    rot, M, Minv = rot_mod.rotate_keep_center(gray, angle_deg)
    try:
        x, y, w, h = frame_mod.find_inner_roi(rot, ceramic_min=cfg.ceramic_min,
                                              margin=6)
    except FrameNotFound as e:
        raise FrameNotFound("edge_pairing post-rotation: %s" % e)
    region = Rect(x, y, w, h)

    inset = EDGE_PAIR_INSET_PX
    x0, y0 = region.x + inset, region.y + inset
    x1, y1 = region.x + region.w - inset, region.y + region.h - inset
    if x1 - x0 < 20 or y1 - y0 < 20:
        return DetectionAnomaly(
            roi_used=roi_rect, angle_deg=angle_deg,
            reasons=["INSET_DEGENERATE"],
            detail={"inset_w": x1 - x0, "inset_h": y1 - y0,
                    "edge_pair_inset_px": inset})

    band = EDGE_PAIR_PROFILE_BAND_PX
    min_pitch = DEFAULT_MIN_PITCH_PX
    ratio = cfg.peak_min_dist_ratio
    top = _find_valleys(_edge_profile(rot, x0, y0, x1, y1, "top", band),
                        min_pitch, ratio)
    bottom = _find_valleys(_edge_profile(rot, x0, y0, x1, y1, "bottom", band),
                           min_pitch, ratio)
    left = _find_valleys(_edge_profile(rot, x0, y0, x1, y1, "left", band),
                         min_pitch, ratio)
    right = _find_valleys(_edge_profile(rot, x0, y0, x1, y1, "right", band),
                          min_pitch, ratio)
    logger.debug("edge_pairing valleys top=%d bottom=%d left=%d right=%d",
                len(top), len(bottom), len(left), len(right))

    if len(top) == len(bottom) + 1:
        bottom = _complete_missing_valley(bottom, top)
    elif len(bottom) == len(top) + 1:
        top = _complete_missing_valley(top, bottom)
    if len(left) == len(right) + 1:
        right = _complete_missing_valley(right, left)
    elif len(right) == len(left) + 1:
        left = _complete_missing_valley(left, right)

    reasons = []
    detail = {"top": len(top), "bottom": len(bottom),
             "left": len(left), "right": len(right)}
    if len(top) != len(bottom) or len(top) < 2:
        reasons.append("COUNT_MISMATCH_V")
    if len(left) != len(right) or len(left) < 2:
        reasons.append("COUNT_MISMATCH_H")
    if reasons:
        logger.debug("edge_pairing count mismatch: %r detail=%r",
                    reasons, detail)
        return DetectionAnomaly(roi_used=roi_rect, angle_deg=angle_deg,
                                reasons=reasons, detail=detail)

    fam_details = []
    defects_out = []
    lines_total = 0
    for axis, edge_a, edge_b in (("v", top, bottom), ("h", left, right)):
        positions = []
        lengths = []
        n = len(edge_a)
        for i in range(n):
            if axis == "v":
                p1 = (x0 + edge_a[i], float(y0))
                p2 = (x0 + edge_b[i], float(y1))
            else:
                p1 = (float(x0), y0 + edge_a[i])
                p2 = (float(x1), y0 + edge_b[i])
            ep1, ep2 = _line_frame_intersection(p1, p2, region, axis)
            prof = _line_profile(rot, ep1, ep2, EDGE_PAIR_PROFILE_BAND_PX)
            inverted = 255.0 - prof
            runs = breaks_mod.find_dark_runs(
                inverted, bright_thresh=EDGE_PAIR_CUT_THRESH,
                min_len=EDGE_PAIR_MIN_BREAK_PX,
                gap_merge_px=EDGE_PAIR_GAP_MERGE_PX,
                edge_guard_px=EDGE_PAIR_EDGE_GUARD_PX)
            lid = lines_total + i + 1
            length_sum = 0.0
            denom = max(1, len(prof) - 1)
            for s, e in runs:
                t0, t1 = s / denom, e / denom
                bx1 = ep1[0] + (ep2[0] - ep1[0]) * t0
                by1 = ep1[1] + (ep2[1] - ep1[1]) * t0
                bx2 = ep1[0] + (ep2[0] - ep1[0]) * t1
                by2 = ep1[1] + (ep2[1] - ep1[1]) * t1
                pts = rot_mod.map_points_back(
                    np.array([(bx1, by1), (bx2, by2)]), Minv)
                length_px = float(e - s + 1)
                defects_out.append(BreakDefect(
                    line_id=lid,
                    x1=round(float(pts[0, 0]), 1),
                    y1=round(float(pts[0, 1]), 1),
                    x2=round(float(pts[1, 0]), 1),
                    y2=round(float(pts[1, 1]), 1),
                    length_px=round(length_px, 1), axis=axis))
                length_sum += length_px
            pos = (edge_a[i] + edge_b[i]) / 2.0 + (x0 if axis == "v" else y0)
            positions.append(pos)
            lengths.append(length_sum)
        fam_details.append(FamilyDetection(
            axis=axis, angle_deg=round(angle_deg, 3),
            pitch_px=round(_est_pitch(edge_a), 2),
            positions_px=positions, region=region, mode="edge_pairing",
            break_lengths_px=lengths))
        lines_total += n
        logger.debug("edge_pairing axis=%s n=%d pitch=%.2f",
                    axis, n, _est_pitch(edge_a))

    return fam_details, defects_out, lines_total
