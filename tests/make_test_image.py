# -*- coding: utf-8 -*-
"""合成測試圖產生器：黑框 + 陶瓷底色 + 暗線網格（實機極性，見需求 2）。

build(with_breaks) -> (img, ground_truth)
    img: 3840x2748 uint8 灰階，整張已疊加 ANGLE_DEG 模擬實機放置角
    ground_truth: [(axis, pos, start, end), ...]，斷點在**旋轉前**
                  軸對齊座標系的位置（僅供人工核對，characterization
                  測試只比對斷點數量）

斷點做法：該段線還原成陶瓷底色（沒有真的刻出暗溝）——對應需求 2
「亮段（高於門檻）視為斷線」：intact 暗線反相後是亮峰，斷點處反相後
只剩陶瓷底色的中等亮度，被 cut_bright_thresh 判定為斷線。

只給 tests/record_golden.py 使用，非 pytest 測試本身。
"""
import cv2
import numpy as np

WIDTH, HEIGHT = 3840, 2748
FRAME_VAL = 20
CERAMIC_VAL = 130
LINE_VAL = 40
LINE_THICK = 7
PITCH = 130.0
ANGLE_DEG = 1.5
INTERIOR = (400, 370, 3440, 2380)      # x0, y0, x1, y1（旋轉前）
MARGIN_IN = 200                         # 內縮，避免線貼著內緣（見需求 4
# 交叉驗證：小方框四邊因 ANGLE_DEG 傾斜，同一條線在對側邊界的交點會
# 有 ~高度*tan(ANGLE_DEG) 的水平位移，邊界線需要留夠餘裕才能四邊都測到）


def build(with_breaks: bool):
    img = np.full((HEIGHT, WIDTH), FRAME_VAL, dtype=np.uint8)
    x0, y0, x1, y1 = INTERIOR
    img[y0:y1, x0:x1] = CERAMIC_VAL

    v_xs = [int(round(x)) for x in np.arange(x0 + MARGIN_IN, x1 - MARGIN_IN, PITCH)]
    h_ys = [int(round(y)) for y in np.arange(y0 + MARGIN_IN, y1 - MARGIN_IN, PITCH)]

    half = LINE_THICK // 2
    for xi in v_xs:
        img[y0:y1, xi - half:xi + half + 1] = LINE_VAL
    for yi in h_ys:
        img[yi - half:yi + half + 1, x0:x1] = LINE_VAL

    # 斷點矩形要比 band_profile 的取樣帶（pos ± band_halfwidth_px，
    # 預設 4）更寬，否則另一族的線整寬跨過斷點列/行時，取樣帶邊緣會
    # 露出一小截另一族線段（同時是亮線，反相後看起來像沒斷），把一個
    # 斷點誤判成兩段；同時斷點矩形本身也不能碰到另一族線的本體，
    # 否則會意外把那條線也弄出一小段假斷點——故斷點視窗夾在兩條
    # 另一族線之間、留 clear 的安全距離。
    break_half = 6
    clear = break_half + half + 5
    ground_truth = []
    if with_breaks:
        bx = v_xs[5]
        by0, by1 = h_ys[3] + clear, h_ys[4] - clear
        img[by0:by1, bx - break_half:bx + break_half + 1] = CERAMIC_VAL
        ground_truth.append(("v", bx, by0, by1))

        hy = h_ys[6]
        hx0, hx1 = v_xs[8] + clear, v_xs[9] - clear
        img[hy - break_half:hy + break_half + 1, hx0:hx1] = CERAMIC_VAL
        ground_truth.append(("h", hy, hx0, hx1))

    center = (WIDTH / 2.0, HEIGHT / 2.0)
    M = cv2.getRotationMatrix2D(center, ANGLE_DEG, 1.0)
    # 最近鄰插值：合成圖只有 3 個固定灰階值，線性插值會在線/斷點邊界
    # 產生次像素模糊，容易讓一個斷點被 gap_merge_px 判成沒接住的兩段
    # ——不是演算法錯，是合成圖本身該避免的雜訊，用最近鄰保持硬邊界。
    rotated = cv2.warpAffine(img, M, (WIDTH, HEIGHT), flags=cv2.INTER_NEAREST,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated, ground_truth
