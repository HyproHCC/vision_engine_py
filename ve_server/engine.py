# -*- coding: utf-8 -*-
"""協定 <-> ve_core 轉接層。

ve_core 是純演算法（無 I/O）；本檔負責 server 側的「不純」部分：
- 影像載入（fromfile+imdecode，CP950 環境下 cv2.imread 對路徑編碼脆弱）
- NG 影像留存複製
- req dict -> ve_core 型別（RoiSpec / TaughtParams）
- ve_core 例外 -> PROTOCOL.md 第 9 節 error_code
- ve_core dataclass -> 協定回應欄位 dict（欄位與舊版 pipeline 輸出一致）
"""
import os

import cv2
import numpy as np

import ve_core
from .protocol import (E_FRAME_NOT_FOUND, E_IMAGE_LOAD_FAIL,
                       E_IMAGE_NOT_FOUND, E_LINES_NOT_FOUND,
                       E_TAUGHT_PARAMS_BAD, ProtocolError)


def load_gray(image_path: str) -> np.ndarray:
    if not os.path.isfile(image_path):
        raise ProtocolError(E_IMAGE_NOT_FOUND,
                            "image not found: %s" % image_path)
    data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ProtocolError(E_IMAGE_LOAD_FAIL,
                            "image load failed: %s" % image_path)
    return img


def _rect_from_wire(d: dict) -> ve_core.Rect:
    """LabVIEW Rectangle cluster（IMAQ 慣例：right/bottom 不含）-> ve_core.Rect。
    同時支援 {x, y, w, h} 以相容直接調用 engine.inspect 的測試。"""
    if "x" in d:
        return ve_core.Rect(int(d["x"]), int(d["y"]), int(d["w"]), int(d["h"]))
    left, top = int(d["left"]), int(d["top"])
    return ve_core.Rect(left, top, int(d["right"]) - left, int(d["bottom"]) - top)


def _rect_to_wire(r: ve_core.Rect) -> dict:
    """ve_core.Rect -> LabVIEW Rectangle cluster（right/bottom 不含）。"""
    return {"left": r.x, "top": r.y, "right": r.x + r.w, "bottom": r.y + r.h}


def _roi_spec(req: dict) -> ve_core.RoiSpec:
    if req.get("roi_mode", "AutoFrame") == "Manual":
        return ve_core.RoiSpec("Manual", _rect_from_wire(req["roi_rect"]))
    return ve_core.RoiSpec("AutoFrame")


class Engine:
    """真實模式的指令實作。mock 模式不會建立本類（不 import cv2 的
    要求由 dispatcher 的延遲 import 滿足）。"""

    def __init__(self, algo_cfg: dict, ng_dir: str, logger):
        self.cfg = ve_core.AlgoConfig.from_dict(algo_cfg)
        self.ng_dir = ng_dir
        self.logger = logger

    # ---- inspect ----
    def inspect(self, req: dict) -> dict:
        gray = load_gray(req["image_path"])
        roi = _roi_spec(req)
        tol = float(req.get("angle_tol_deg", 5.0))

        taught = None
        if req.get("param_source") == "Taught":
            try:
                taught = ve_core.TaughtParams.from_json_dict(
                    req.get("taught_params"))
            except ve_core.TaughtParamsError as e:
                raise ProtocolError(E_TAUGHT_PARAMS_BAD, str(e))

        try:
            result = ve_core.inspect(gray, self.cfg, roi,
                                     angle_tol_deg=tol, taught=taught)
        except ve_core.FrameNotFound as e:
            raise ProtocolError(E_FRAME_NOT_FOUND, str(e))
        except ve_core.LinesNotFound as e:
            raise ProtocolError(E_LINES_NOT_FOUND, str(e))

        if isinstance(result, ve_core.PlacementResult):
            return {"status": "PLACEMENT_ERROR",
                    "angle_deg": result.angle_deg,
                    "lines_found": 0, "defects": [],
                    "v_break_lengths_px": [], "h_break_lengths_px": [],
                    "roi_used": _rect_to_wire(result.roi_used),
                    "detection_mode": "n/a", "ng_image_path": ""}

        if isinstance(result, ve_core.DetectionAnomaly):
            return {"status": "DETECTION_ANOMALY",
                    "angle_deg": result.angle_deg,
                    "lines_found": 0, "defects": [],
                    "v_break_lengths_px": [], "h_break_lengths_px": [],
                    "roi_used": _rect_to_wire(result.roi_used),
                    "detection_mode": "n/a", "reason_codes": result.reasons,
                    "ng_image_path": ""}

        ng_path = ""
        if result.defects:
            ng_path = self._save_ng_copy(req["image_path"])

        lengths = result.break_lengths_json()
        return {"status": result.verdict.value,
                "angle_deg": result.angle_deg,
                "lines_found": result.lines_found,
                "defects": result.defects_json(),
                "v_break_lengths_px": lengths["v"],
                "h_break_lengths_px": lengths["h"],
                "roi_used": _rect_to_wire(result.roi_used),
                "detection_mode": result.detection_mode,
                "ng_image_path": ng_path}

    # ---- teach ----
    def teach(self, req: dict) -> dict:
        gray = load_gray(req["image_path"])
        roi = _roi_spec(req)
        tol = float(req.get("angle_tol_deg", 5.0))

        try:
            result = ve_core.teach(
                gray, self.cfg, roi, angle_tol_deg=tol,
                image_name=os.path.basename(req["image_path"]))
        except ve_core.FrameNotFound as e:
            raise ProtocolError(E_FRAME_NOT_FOUND, str(e))
        except ve_core.LinesNotFound as e:
            raise ProtocolError(E_LINES_NOT_FOUND, str(e))

        if isinstance(result, ve_core.PlacementResult):
            return {"status": "PLACEMENT_ERROR",
                    "angle_deg": result.angle_deg,
                    "roi_used": _rect_to_wire(result.roi_used)}

        return {"status": "OK",
                "angle_deg": result.angle_deg,
                "roi_used": _rect_to_wire(result.roi_used),
                "taught_params": result.taught.to_json_dict(),
                "preview": result.preview_json()}

    # ---- NG retention ----
    def _save_ng_copy(self, image_path: str) -> str:
        """NG 影像留存（複製原圖，不覆寫同名檔）。失敗不影響檢測結果。"""
        try:
            os.makedirs(self.ng_dir, exist_ok=True)
            base = os.path.basename(image_path)
            dst = os.path.join(self.ng_dir, base)
            n = 1
            stem, ext = os.path.splitext(base)
            while os.path.exists(dst):
                dst = os.path.join(self.ng_dir, "%s_%d%s" % (stem, n, ext))
                n += 1
            with open(image_path, "rb") as fsrc, open(dst, "wb") as fdst:
                fdst.write(fsrc.read())
            return dst.replace("\\", "/")
        except Exception as e:
            self.logger.warning("NG copy failed: %s", e)
            return ""
