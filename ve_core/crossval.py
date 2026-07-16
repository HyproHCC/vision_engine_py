# -*- coding: utf-8 -*-
"""框邊配對法交叉驗證（需求 4）：獨立於投影找線法之外的第二道把關。

原理：大黑框內緣（roi_rect，原圖座標）往內縮固定距離成一個小方框，
沿小方框四邊取剖面（垂直邊方向鄰近 band 平均），找谷點——切割線是
暗線，經過框邊時在剖面上是谷。同一條線會在兩個對側邊界上都留下
一個谷點（v 族切過 top/bottom，h 族切過 left/right），配對後可以
獨立算出「這條線自己的角度」，不靠去旋轉座標系、不靠投影找線法。

三項檢查：
  (a) 同族線角度離散度（配對算出的角度）≤ 容差
  (b) 兩族代表角度夾角與 90° 相差 ≤ 容差
  (c) 兩側谷點數與投影找線法找到的線數一致
任一失敗即回報 DetectionAnomaly（可能同時多個原因），全過回傳 None。

只在 pipeline.inspect() 呼叫（teach() 不驗證，教導本身有操作員目視把關）。
"""
import math
from typing import Optional

import numpy as np

from .lines import DEFAULT_MIN_PITCH_PX, estimate_pitch_from_peaks
from .types import AlgoConfig, DetectionAnomaly, Rect


def _edge_profile(gray: np.ndarray, x0: int, y0: int, x1: int, y1: int,
                  edge: str, band_px: int) -> np.ndarray:
    """沿小方框某一邊取剖面，每點＝垂直邊方向 ±band_px 鄰域平均。"""
    if edge in ("top", "bottom"):
        y = y0 if edge == "top" else y1
        lo = max(0, y - band_px)
        hi = min(gray.shape[0], y + band_px + 1)
        return gray[lo:hi, x0:x1].mean(axis=0).astype(np.float64)
    x = x0 if edge == "left" else x1
    lo = max(0, x - band_px)
    hi = min(gray.shape[1], x + band_px + 1)
    return gray[y0:y1, lo:hi].mean(axis=1).astype(np.float64)


def _find_valleys(profile: np.ndarray, min_pitch: int,
                  peak_min_dist_ratio: float) -> list:
    """暗線在剖面上是谷；重用 estimate_pitch_from_peaks 對負值取峰＝找谷
    （而非單純呼叫 find_peaks(min_dist=min_pitch)）——單純用寬鬆固定
    min_dist 找峰，會跟 lines.py 找線一樣把同一個谷點旁的雜訊子峰
    誤判成好幾個獨立谷點（見 ARCHITECTURE.md §8「合成旋轉下找線數
    暴增」的同一種根因），此處直接借用該函式已驗證過的收斂邏輯。"""
    if len(profile) < min_pitch * 2:
        return []
    _, peaks = estimate_pitch_from_peaks(-profile, min_pitch,
                                         peak_min_dist_ratio)
    return peaks


def _pair_angles(idx_a: list, idx_b: list, span: float) -> list:
    """依序排序後兩兩配對（同一條線在兩側的谷點應保持左右/上下順序不變），
    回傳每一對算出的角度（deg，相對邊法向的偏角）。"""
    n = min(len(idx_a), len(idx_b))
    angles = []
    for i in range(n):
        angles.append(math.degrees(math.atan2(idx_b[i] - idx_a[i], span)))
    return angles


def cross_validate(gray: np.ndarray, roi_rect: Rect, angle_deg: float,
                   v_count: int, h_count: int,
                   cfg: AlgoConfig) -> Optional[DetectionAnomaly]:
    """回 None 表示通過；否則回傳 DetectionAnomaly（reasons 可能多個）。"""
    # roi_rect 是軸對齊的內緣框；片子本身有 angle_deg 的放置角時，
    # find_inner_roi 的列/行亮像素比例門檻（frac=0.05）在框角附近容易
    # 因為傾斜楔形只需一小截亮像素就通過，讓 roi_rect 仍帶一小塊黑框
    # 楔形。固定內縮距離不足以在有效放置角範圍內清掉這塊楔形（楔形深度
    # 隨邊長與 sin(angle) 增加），故內縮距離依實測角度動態加大。
    tilt_wedge = int(np.ceil(max(roi_rect.w, roi_rect.h) *
                             abs(np.sin(np.radians(angle_deg)))))
    inset = int(cfg.xval_inset_px) + tilt_wedge
    band = int(cfg.xval_edge_band_px)
    x0, y0 = roi_rect.x + inset, roi_rect.y + inset
    x1, y1 = roi_rect.x + roi_rect.w - inset, roi_rect.y + roi_rect.h - inset
    w, h = x1 - x0, y1 - y0
    if w < 20 or h < 20:
        return DetectionAnomaly(
            roi_used=roi_rect, angle_deg=angle_deg,
            reasons=["INSET_DEGENERATE"],
            detail={"inset_w": w, "inset_h": h, "xval_inset_px": inset})

    min_pitch = DEFAULT_MIN_PITCH_PX
    ratio = cfg.peak_min_dist_ratio
    top = _find_valleys(_edge_profile(gray, x0, y0, x1, y1, "top", band),
                        min_pitch, ratio)
    bottom = _find_valleys(_edge_profile(gray, x0, y0, x1, y1, "bottom", band),
                           min_pitch, ratio)
    left = _find_valleys(_edge_profile(gray, x0, y0, x1, y1, "left", band),
                         min_pitch, ratio)
    right = _find_valleys(_edge_profile(gray, x0, y0, x1, y1, "right", band),
                          min_pitch, ratio)

    v_angles = _pair_angles(top, bottom, float(h)) if v_count > 0 else []
    h_angles = _pair_angles(left, right, float(w)) if h_count > 0 else []

    reasons = []
    detail = {"v_edge_counts": {"top": len(top), "bottom": len(bottom)},
             "h_edge_counts": {"left": len(left), "right": len(right)},
             "v_count": v_count, "h_count": h_count}

    # (a) 同族角度離散度
    if len(v_angles) >= 2:
        disp = max(v_angles) - min(v_angles)
        detail["v_angle_dispersion"] = disp
        if disp > cfg.xval_angle_dispersion_tol_deg:
            reasons.append("ANGLE_DISPERSION_V")
    if len(h_angles) >= 2:
        disp = max(h_angles) - min(h_angles)
        detail["h_angle_dispersion"] = disp
        if disp > cfg.xval_angle_dispersion_tol_deg:
            reasons.append("ANGLE_DISPERSION_H")

    # (b) 兩族夾角 90°±容差
    # v_angles 是「偏離垂直軸」的角度、h_angles 是「偏離水平軸」的角度，
    # 垂直與水平本身已經正交；兩族真正的夾角＝90°＋(v_repr－h_repr)，
    # 所以「與 90° 相差多少」就是 |v_repr－h_repr| 本身，不必再減 90。
    if v_angles and h_angles:
        v_repr = float(np.median(v_angles))
        h_repr = float(np.median(h_angles))
        perp_err = abs(v_repr - h_repr)
        detail["perp_err_deg"] = perp_err
        if perp_err > cfg.xval_perp_tol_deg:
            reasons.append("PERPENDICULARITY")

    # (c) 谷點數與投影找線數一致（容許 ±1：peak 判準要求兩側鄰居都存在，
    # 最外側那條線的谷點若剛好落在剖面陣列頭尾，結構上就是測不到，
    # 跟真的漏偵測是兩回事，故留 1 條的數值容差，2 條以上才算異常）
    if v_count > 0:
        if abs(len(top) - v_count) > 1 or abs(len(bottom) - v_count) > 1:
            reasons.append("COUNT_MISMATCH_V")
    if h_count > 0:
        if abs(len(left) - h_count) > 1 or abs(len(right) - h_count) > 1:
            reasons.append("COUNT_MISMATCH_H")

    if not reasons:
        return None
    return DetectionAnomaly(roi_used=roi_rect, angle_deg=angle_deg,
                            reasons=reasons, detail=detail)
