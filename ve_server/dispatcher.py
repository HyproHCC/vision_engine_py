# -*- coding: utf-8 -*-
"""指令分派：ping / inspect / teach / shutdown。

- mock 模式不 import cv2（LabVIEW 端可在無 OpenCV 環境離線開發）
- 真實模式延遲載入 engine（ve_core 轉接層）
- NG 留存清理（retention days）在啟動與每次 inspect 後執行
"""
import glob
import os
import time

from . import protocol as P
from .config import SERVER_VERSION


class Dispatcher:
    def __init__(self, cfg: dict, logger, mock: bool = False):
        self.cfg = cfg
        self.logger = logger
        self.mock = mock
        self.t_boot = time.monotonic()
        self._mock_seq = 0
        self._engine = None
        if not mock:
            from .engine import Engine  # 延遲到這裡才 import cv2
            self._engine = Engine(cfg["algo"], cfg["ng_dir"], logger)
            self.cleanup_ng()

    # ---- public ----
    def handle(self, req: dict) -> tuple:
        """回 (resp_dict, shutdown_flag)。"""
        t0 = time.perf_counter()
        cmd = req["cmd"]
        try:
            if cmd == "ping":
                return self._ping(req, t0), False
            if cmd == "shutdown":
                return P.build_response(req, P.S_OK, t_start=t0), True
            if cmd == "inspect":
                return self._inspect(req, t0), False
            if cmd == "teach":
                return self._teach(req, t0), False
        except P.ProtocolError as e:
            self.logger.warning("%s failed: [%d] %s", cmd, e.code, e.msg)
            return P.build_error_response(req, e.code, e.msg, t0), False
        except Exception as e:  # 不讓任何例外殺掉 server
            self.logger.exception("internal error in %s", cmd)
            return P.build_error_response(req, P.E_INTERNAL,
                                          "internal: %s" % e, t0), False
        return P.build_error_response(req, P.E_UNKNOWN_CMD, cmd, t0), False

    # ---- handlers ----
    def _ping(self, req, t0):
        return P.build_response(req, P.S_OK, t_start=t0,
                                server_version=SERVER_VERSION,
                                mock=self.mock,
                                uptime_s=round(time.monotonic() - self.t_boot, 1))

    def _inspect(self, req, t0):
        if self.mock:
            return self._mock_inspect(req, t0)
        result = self._engine.inspect(req)
        if self.cfg.get("cleanup_on_inspect", True):
            self.cleanup_ng()
        status = result.pop("status")
        self.logger.info("inspect %s -> %s (%d defects)",
                         req.get("piece_id", "?"), status,
                         len(result.get("defects", [])))
        return P.build_response(req, status, t_start=t0, **result)

    def _teach(self, req, t0):
        if self.mock:
            return self._mock_teach(req, t0)
        result = self._engine.teach(req)
        status = result.pop("status")
        return P.build_response(req, status, t_start=t0, **result)

    # ---- mock ----
    def _mock_inspect(self, req, t0):
        self._mock_seq += 1
        phase = self._mock_seq % 4
        common = dict(detection_mode="mock", lines_found=24,
                      roi_used={"left": 412, "top": 380,
                                "right": 3422, "bottom": 2368})
        if phase == 1:
            return P.build_response(
                req, P.S_OK, t_start=t0, angle_deg=0.42,
                defects=[], ng_image_path="",
                v_break_lengths_px=[0.0] * 14, h_break_lengths_px=[0.0] * 10,
                **common)
        if phase == 2:
            defects = [
                {"line_id": 3, "x1": 1204.5, "y1": 812.0,
                 "x2": 1204.5, "y2": 951.0, "length_px": 139.0},
                {"line_id": 7, "x1": 2110.0, "y1": 1433.5,
                 "x2": 2251.0, "y2": 1433.5, "length_px": 141.0},
            ]
            v_lengths = [0.0] * 14
            v_lengths[2] = 139.0
            h_lengths = [0.0] * 10
            h_lengths[1] = 141.0
            return P.build_response(
                req, P.S_NG, t_start=t0, angle_deg=1.31,
                defects=defects, ng_image_path="MOCK/ng/fake.png",
                v_break_lengths_px=v_lengths, h_break_lengths_px=h_lengths,
                **common)
        if phase == 3:
            return P.build_response(
                req, P.S_PLACEMENT, t_start=t0, angle_deg=6.8,
                lines_found=0, defects=[], ng_image_path="",
                v_break_lengths_px=[], h_break_lengths_px=[],
                detection_mode="mock",
                roi_used={"left": 0, "top": 0, "right": 0, "bottom": 0})
        return P.build_response(
            req, P.S_DETECTION_ANOMALY, t_start=t0, angle_deg=1.28,
            lines_found=0, defects=[], ng_image_path="",
            v_break_lengths_px=[], h_break_lengths_px=[],
            detection_mode="mock",
            reason_codes=["COUNT_MISMATCH_V"],
            roi_used={"left": 412, "top": 380, "right": 3422, "bottom": 2368})

    def _mock_teach(self, req, t0):
        tp = {
            "tp_version": 1,
            "families": [
                {"axis": "v", "angle_deg": 1.32, "pitch_px": 130.4,
                 "line_count": 3, "positions_px": [412.0, 542.5, 673.1]},
                {"axis": "h", "angle_deg": 1.35, "pitch_px": 130.1,
                 "line_count": 2, "positions_px": [380.0, 510.2]},
            ],
            "thresholds": {"cut_bright_thresh": 180, "min_break_len_px": 8,
                           "band_halfwidth_px": 4},
            "reference": {"taught_at": "2026-01-01T00:00:00",
                          "image": "mock.png"},
        }
        preview = {"families": [
            {"axis": "v", "angle_deg": 1.32, "line_count": 3, "pitch_px": 130.4},
            {"axis": "h", "angle_deg": 1.35, "line_count": 2, "pitch_px": 130.1},
        ]}
        return P.build_response(
            req, P.S_OK, t_start=t0, angle_deg=1.32,
            roi_used={"left": 412, "top": 380, "right": 3422, "bottom": 2368},
            taught_params=tp, preview=preview)

    # ---- NG retention ----
    def cleanup_ng(self):
        days = int(self.cfg.get("ng_retention_days", 0))
        if days <= 0:
            return
        cutoff = time.time() - days * 86400
        try:
            for p in glob.glob(os.path.join(self.cfg["ng_dir"], "*.png")):
                if os.path.getmtime(p) < cutoff:
                    os.remove(p)
                    self.logger.info("NG retention: removed %s", p)
        except Exception as e:
            self.logger.warning("NG cleanup failed: %s", e)
