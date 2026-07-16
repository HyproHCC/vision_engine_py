# -*- coding: utf-8 -*-
"""切割道斷點偵測（在去旋轉座標系中）。

尚未解決（等對照影像）：暗段是「未切穿」還是「被晶粒遮擋」。
策略：
- 亮度 < cut_bright_thresh 的連續區段長度 >= min_break_len_px 才回報
- **所有門檻都來自 Thresholds**（taught_params.thresholds 或 AlgoConfig），
  對照影像量化後只改參數不改碼
- 若日後確認需要「排除晶粒遮擋段」，遮罩邏輯加在 profile.py（介面不變）

TODO(對照影像): 用已知切穿 vs 未切穿同位置影像量化分離度，
  定 cut_bright_thresh 與 min_break_len_px；必要時改為
  「相對門檻」（該線亮段中位數的比例）以抗照明漂移。
"""
import numpy as np

from .profile import band_profile
from .types import Thresholds


def find_dark_runs(profile: np.ndarray, bright_thresh: float,
                   min_len: int, gap_merge_px: int = 0,
                   edge_guard_px: int = 0) -> list:
    """回傳 [(start, end_inclusive), ...]，剖面低於門檻的連續區段。

    gap_merge_px: 兩暗段間的亮 gap <= 此值時合併（交叉切割線寬約 3px，
                  會把一個斷點切成兩段，需要縫回去）
    edge_guard_px: 忽略距剖面兩端此距離內的暗段（線末端與框緣過渡帶）
    """
    dark = profile < bright_thresh
    raw = []
    start = None
    for i, d in enumerate(dark):
        if d and start is None:
            start = i
        elif not d and start is not None:
            raw.append((start, i - 1))
            start = None
    if start is not None:
        raw.append((start, len(dark) - 1))

    # 合併小 gap
    merged = []
    for s, e in raw:
        if merged and s - merged[-1][1] - 1 <= gap_merge_px:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))

    # 邊界保護帶 + 最小長度
    lo, hi = edge_guard_px, len(profile) - 1 - edge_guard_px
    out = []
    for s, e in merged:
        s2, e2 = max(s, lo), min(e, hi)
        if e2 >= s2 and e2 - s2 + 1 >= min_len:
            out.append((s2, e2))
    return out


def detect_breaks_on_line(rot_gray: np.ndarray, axis: str, line_id: int,
                          pos: float, thresholds: Thresholds) -> list:
    """單條線的斷點偵測。回傳去旋轉座標系中的 defect dict 清單。
    座標軸定義：axis='v' 線沿 y 走 → 斷點 (pos, s)~(pos, e)。"""
    prof = band_profile(rot_gray, axis, pos,
                        int(thresholds.band_halfwidth_px))
    runs = find_dark_runs(prof,
                          float(thresholds.cut_bright_thresh),
                          int(thresholds.min_break_len_px),
                          gap_merge_px=int(thresholds.gap_merge_px),
                          edge_guard_px=int(thresholds.edge_guard_px))
    defects = []
    for s, e in runs:
        if axis == "v":
            p1 = (pos, float(s))
            p2 = (pos, float(e))
        else:
            p1 = (float(s), pos)
            p2 = (float(e), pos)
        defects.append({
            "line_id": line_id,
            "_p1_rot": p1, "_p2_rot": p2,   # 去旋轉座標，pipeline 負責轉回原圖
            "length_px": float(e - s + 1),
        })
    return defects
