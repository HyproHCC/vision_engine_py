# -*- coding: utf-8 -*-
"""大黑框內緣定位（AutoFrame）。

實測灰階：黑框/晶粒 ~15-20、陶瓷區 ~100-150、透光 200+。
黑框在治具遮擋處會與影像外圍暗背景相連，因此不用連通區塊，
改用「由外往內掃描列/行投影，找第一個穩定進入亮區的位置」。

判準：該列(行)中灰階 >= ceramic_min 的像素比例超過 frac，
且連續 run_need 列(行)都成立，取 run 的起點為內緣。
晶粒是黑的，但切割道與陶瓷邊緣透亮，內部區域的亮像素比例
遠高於黑框區（黑框幾乎 0%），此判準對晶粒排列不敏感。
"""
import numpy as np

from .errors import FrameNotFound


def _scan_edge(bright_frac: np.ndarray, frac: float, run_need: int, reverse: bool):
    idx = range(len(bright_frac) - 1, -1, -1) if reverse else range(len(bright_frac))
    run = 0
    for i in idx:
        if bright_frac[i] >= frac:
            run += 1
            if run >= run_need:
                return (i + run_need - 1) if reverse else (i - run_need + 1)
        else:
            run = 0
    return None


def find_inner_roi(gray: np.ndarray, ceramic_min: int = 90,
                   frac: float = 0.05, run_need: int = 12,
                   margin: int = 4) -> tuple:
    """回傳大黑框內部 ROI (x, y, w, h)，原圖座標。

    frac: 一列(行)中亮像素(>=ceramic_min)比例門檻。黑框區幾乎為 0，
          內部區至少有切割道與陶瓷露出，5% 是保守值。
    run_need: 連續成立的列(行)數，濾掉雜訊亮點。
    margin: 內縮像素，避免貼著框緣的陰影過渡帶。
    """
    bright = (gray >= ceramic_min)
    row_frac = bright.mean(axis=1)   # 每列亮像素比例
    col_frac = bright.mean(axis=0)   # 每行亮像素比例

    top = _scan_edge(row_frac, frac, run_need, reverse=False)
    bottom = _scan_edge(row_frac, frac, run_need, reverse=True)
    left = _scan_edge(col_frac, frac, run_need, reverse=False)
    right = _scan_edge(col_frac, frac, run_need, reverse=True)

    if top is None or bottom is None or left is None or right is None:
        raise FrameNotFound("inner frame boundary not found")
    top += margin
    left += margin
    bottom -= margin
    right -= margin
    if bottom - top < 100 or right - left < 100:
        raise FrameNotFound("inner ROI degenerate (%d x %d)" %
                            (right - left, bottom - top))
    return (int(left), int(top), int(right - left + 1), int(bottom - top + 1))
