# -*- coding: utf-8 -*-
"""沿切割道的剖面萃取。

已驗證：沿切割道亮度最大值在 44–208 間變動，透亮/暗段交替明顯。
剖面取「線位置 ± band_halfwidth 內的橫向最大值」——線可能有
次像素偏移與雙峰結構，取帶內最大值可容忍。

日後「雙峰結構分析」「晶粒遮擋遮罩」等剖面級處理加在本檔，
breaks.py 的判定介面不變。
"""
import numpy as np


def band_profile(rot_gray: np.ndarray, axis: str, pos: float,
                 band_halfwidth_px: int) -> np.ndarray:
    """取線位置 ± halfwidth 帶內、垂直於線方向的最大值 → 沿線剖面。"""
    p = int(round(pos))
    if axis == "v":
        lo = max(0, p - band_halfwidth_px)
        hi = min(rot_gray.shape[1], p + band_halfwidth_px + 1)
        return rot_gray[:, lo:hi].max(axis=1).astype(np.float64)
    lo = max(0, p - band_halfwidth_px)
    hi = min(rot_gray.shape[0], p + band_halfwidth_px + 1)
    return rot_gray[lo:hi, :].max(axis=0).astype(np.float64)
