# -*- coding: utf-8 -*-
"""影像載入（調機工具側 I/O）。

CP950 地區 cv2.imread 對中文路徑會**靜默失敗**（回 None）——
協定路徑雖限 ASCII，但工程師調機資料夾幾乎必有中文，
一律用 fromfile + imdecode。
"""
import os

import cv2
import numpy as np

IMAGE_EXTS = (".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff")


def load_gray(path: str) -> np.ndarray:
    """載入灰階影像。失敗丟 IOError（含路徑供 UI 顯示）。"""
    if not os.path.isfile(path):
        raise IOError("找不到影像檔：%s" % path)
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise IOError("影像載入失敗（格式壞損？）：%s" % path)
    return img


def list_images(folder: str) -> list:
    """資料夾內影像檔清單（批次跑分用），依檔名排序。"""
    out = []
    for name in sorted(os.listdir(folder)):
        if os.path.splitext(name)[1].lower() in IMAGE_EXTS:
            out.append(os.path.join(folder, name))
    return out
