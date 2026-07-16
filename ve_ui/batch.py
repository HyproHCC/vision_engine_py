# -*- coding: utf-8 -*-
"""批次跑分：資料夾內全部影像以目前參數執行完整檢測。

在獨立 QThread 執行、使用**參數快照**（不共用 InspectionSession 的
快取，避免執行緒衝突）。每張圖發 progress，全部完成發 finishedRows。
"""
import os
import time

from PySide6.QtCore import QThread, Signal

import ve_core

from .loader import load_gray


class BatchRunner(QThread):
    progress = Signal(int, int, str)         # done, total, current path
    rowReady = Signal(dict)                  # 單張結果列
    finishedRows = Signal(list, list)        # rows, defect_rows

    def __init__(self, paths, cfg: "ve_core.AlgoConfig",
                 thresholds: "ve_core.Thresholds",
                 judge: "ve_core.JudgeCriteria",
                 roi: "ve_core.RoiSpec", angle_tol: float,
                 mode: str, taught, parent=None):
        super().__init__(parent)
        self.paths = list(paths)
        # 快照（dataclass 淺層複製即可，內容皆為值型別）
        self.cfg = ve_core.AlgoConfig.from_dict(cfg.to_dict())
        self.thresholds = ve_core.Thresholds(**thresholds.to_json_dict())
        self.judge = ve_core.JudgeCriteria(judge.judge_max_break_px,
                                           judge.judge_max_breaks)
        self.roi = roi
        self.angle_tol = float(angle_tol)
        self.mode = mode                     # discovery | taught
        self.taught = taught
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        rows = []
        defect_rows = []
        n = len(self.paths)
        # 批次用 cfg：門檻面板現值覆蓋進 cfg，使發現式也吃到調機值
        cfg = ve_core.AlgoConfig.from_dict({**self.cfg.to_dict(),
                                            **self.thresholds.to_json_dict()})
        taught = self.taught if self.mode == "taught" else None
        for i, path in enumerate(self.paths, 1):
            if self._abort:
                break
            row = {"image": os.path.basename(path), "path": path,
                   "status": "", "verdict": "", "angle_deg": "",
                   "lines_found": "", "n_defects": "",
                   "max_break_px": "", "elapsed_ms": "", "error": ""}
            t0 = time.perf_counter()
            try:
                gray = load_gray(path)
                r = ve_core.inspect(gray, cfg, self.roi,
                                    angle_tol_deg=self.angle_tol,
                                    taught=taught)
                if isinstance(r, ve_core.PlacementResult):
                    row.update(status="PLACEMENT_ERROR", verdict="Placement",
                               angle_deg=r.angle_deg, lines_found=0,
                               n_defects=0, max_break_px=0)
                else:
                    verdict = ve_core.reference_judge(r, self.judge).name
                    row.update(status=r.verdict.value, verdict=verdict,
                               angle_deg=r.angle_deg,
                               lines_found=r.lines_found,
                               n_defects=len(r.defects),
                               max_break_px=max((d.length_px
                                                 for d in r.defects),
                                                default=0.0))
                    for d in r.defects:
                        defect_rows.append({
                            "image": row["image"], "line_id": d.line_id,
                            "axis": d.axis, "x1": d.x1, "y1": d.y1,
                            "x2": d.x2, "y2": d.y2,
                            "length_px": d.length_px})
            except (ve_core.VeCoreError, IOError) as e:
                row.update(status="ERROR", verdict="SystemError",
                           error=str(e))
            except Exception as e:      # 批次不因單張爆掉而中斷
                row.update(status="ERROR", verdict="SystemError",
                           error="internal: %s" % e)
            row["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            rows.append(row)
            self.rowReady.emit(row)
            self.progress.emit(i, n, path)
        self.finishedRows.emit(rows, defect_rows)
