# -*- coding: utf-8 -*-
"""旋轉角估計與座標反轉換。

原理：切割道為亮直線。把 ROI 依候選角度旋轉後做軸向投影，
當線與投影軸對齊時投影剖面最「尖」（峰谷分明），以投影變異數
為 sharpness 指標，粗掃 + 細掃找最大值。

兩族線（不保證正交）各自估角：
  axis='v'（近垂直線族）→ 對 x 投影（column sum）
  axis='h'（近水平線族）→ 對 y 投影（row sum）

座標反轉換：所有偵測都在「去旋轉座標系」進行，輸出前用
inverse rotation matrix 轉回原圖座標（協定要求 defects 為原圖座標）。
"""
import cv2
import numpy as np


def _sharpness(gray_small: np.ndarray, angle_deg: float, axis: str) -> float:
    h, w = gray_small.shape
    M = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle_deg, 1.0)
    rot = cv2.warpAffine(gray_small, M, (w, h), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE)
    proj = rot.mean(axis=0) if axis == "v" else rot.mean(axis=1)
    # 去趨勢後取變異數，避免照明梯度干擾
    k = max(9, (len(proj) // 50) | 1)
    trend = cv2.blur(proj.reshape(-1, 1).astype(np.float32), (1, k)).ravel()
    return float(np.var(proj - trend))


def estimate_angle(gray_roi: np.ndarray, axis: str,
                   search_deg: float = 6.0, coarse_step: float = 0.5,
                   fine_step: float = 0.05, max_side: int = 1400) -> float:
    """回傳該線族相對影像軸的偏角（deg，正值 = 影像需逆時針轉回）。"""
    h, w = gray_roi.shape
    scale = min(1.0, max_side / max(h, w))
    small = cv2.resize(gray_roi, None, fx=scale, fy=scale,
                       interpolation=cv2.INTER_AREA) if scale < 1.0 else gray_roi

    # 粗掃
    coarse = np.arange(-search_deg, search_deg + 1e-9, coarse_step)
    scores = [_sharpness(small, a, axis) for a in coarse]
    a0 = float(coarse[int(np.argmax(scores))])
    # 細掃（粗掃最佳點 ± 1 個粗步進）
    fine = np.arange(a0 - coarse_step, a0 + coarse_step + 1e-9, fine_step)
    scores = [_sharpness(small, a, axis) for a in fine]
    return float(fine[int(np.argmax(scores))])


def rotate_keep_center(gray: np.ndarray, angle_deg: float):
    """以中心旋轉，回傳 (rotated, M, Minv)。尺寸不變（±5° 邊角損失可忽略，
    且 AutoFrame ROI 已在框內）。M / Minv 為 2x3 仿射矩陣。"""
    h, w = gray.shape
    center = (w / 2.0, h / 2.0)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    Minv = cv2.invertAffineTransform(M)
    rot = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE)
    return rot, M, Minv


def map_points_back(pts_xy: np.ndarray, Minv: np.ndarray) -> np.ndarray:
    """去旋轉座標系點 → 原圖座標。pts_xy: (N,2)（整張圖座標系）。"""
    pts = np.asarray(pts_xy, dtype=np.float64).reshape(-1, 2)
    ones = np.ones((pts.shape[0], 1))
    return np.hstack([pts, ones]) @ Minv.T  # (N,2)


def map_rect_forward(rect: tuple, M: np.ndarray) -> tuple:
    """原圖座標的矩形 (x,y,w,h) → 旋轉座標系中的內接軸對齊矩形（保守取內接，
    避免把旋轉帶進來的框外區域包進分析範圍）。"""
    x, y, w, h = rect
    corners = np.array([[x, y], [x + w, y], [x, y + h], [x + w, y + h]],
                       dtype=np.float64)
    ones = np.ones((4, 1))
    mapped = np.hstack([corners, ones]) @ M.T
    xs = np.sort(mapped[:, 0])
    ys = np.sort(mapped[:, 1])
    nx, ny = xs[1], ys[1]           # 第二小 = 內接左/上
    nw, nh = xs[2] - xs[1], ys[2] - ys[1]
    return (int(round(nx)), int(round(ny)),
            int(round(nw)), int(round(nh)))
