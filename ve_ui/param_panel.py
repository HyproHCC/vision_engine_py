# -*- coding: utf-8 -*-
"""參數面板：依管線階段分組，動哪組只讓該階段以下重算。

發出 paramsChanged(group, dict)：
    group ∈ roi / angle / lines / thresholds / judge / tol
主視窗 debounce 後交給 InspectionSession.update_params()。
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QPushButton,
                               QSlider, QSpinBox, QVBoxLayout, QWidget)

import ve_core


class ParamPanel(QWidget):
    paramsChanged = Signal(str, dict)
    roiModeChanged = Signal(object)      # ve_core.RoiSpec
    applyAutoFrameRequested = Signal()   # 「套用 AutoFrame 結果為 Manual 起點」

    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = ve_core.AlgoConfig()
        th = ve_core.Thresholds.from_config(cfg)
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        # ---------------- ROI ----------------
        box = QGroupBox("ROI（找框）")
        form = QFormLayout(box)
        self.roi_mode = QComboBox()
        self.roi_mode.addItems(["AutoFrame", "Manual"])
        form.addRow("roi_mode", self.roi_mode)
        # LabVIEW 慣例：左、上、右、下；內部再轉 x/y/w/h（_emit_roi）
        self.roi_left = self._spin(0, 10000, 0)
        self.roi_top = self._spin(0, 10000, 0)
        self.roi_right = self._spin(0, 10000, 0)
        self.roi_bottom = self._spin(0, 10000, 0)
        rowW = QWidget(); row = QHBoxLayout(rowW); row.setContentsMargins(0, 0, 0, 0)
        for lbl, w in (("左", self.roi_left), ("上", self.roi_top),
                       ("右", self.roi_right), ("下", self.roi_bottom)):
            row.addWidget(QLabel(lbl)); row.addWidget(w)
        form.addRow("roi_rect（左/上/右/下）", rowW)
        self.btn_apply_autoframe = QPushButton("套用 AutoFrame 結果為 Manual 起點")
        form.addRow(self.btn_apply_autoframe)
        self.ceramic_min = self._slider_spin(0, 255, cfg.ceramic_min)
        form.addRow("ceramic_min", self.ceramic_min[2])
        root.addWidget(box)

        # ---------------- 角度 ----------------
        box = QGroupBox("去旋轉（估角）")
        form = QFormLayout(box)
        self.angle_search = self._dspin(1.0, 15.0, cfg.angle_search_deg, 0.5)
        self.angle_coarse = self._dspin(0.05, 2.0, cfg.angle_coarse_step, 0.05)
        self.angle_fine = self._dspin(0.01, 0.5, cfg.angle_fine_step, 0.01)
        self.angle_max_side = self._spin(400, 4000, cfg.angle_est_max_side)
        self.angle_tol = self._dspin(0.5, 15.0, 5.0, 0.5)
        form.addRow("angle_search_deg", self.angle_search)
        form.addRow("angle_coarse_step", self.angle_coarse)
        form.addRow("angle_fine_step", self.angle_fine)
        form.addRow("angle_est_max_side", self.angle_max_side)
        form.addRow("angle_tol_deg（放置容差）", self.angle_tol)
        root.addWidget(box)

        # ---------------- 找線 ----------------
        box = QGroupBox("找線")
        form = QFormLayout(box)
        self.peak_ratio = self._dspin(0.2, 0.95, cfg.peak_min_dist_ratio, 0.05)
        form.addRow("peak_min_dist_ratio", self.peak_ratio)
        self.ridge_kernel = self._spin(3, 61, cfg.ridge_kernel_px)
        form.addRow("ridge_kernel_px（細亮脊線帶通核尺寸）", self.ridge_kernel)
        root.addWidget(box)

        # ---------------- 斷線門檻（即時，毫秒級重算）----------------
        box = QGroupBox("斷線門檻（即時）")
        form = QFormLayout(box)
        self.cut_thresh = self._slider_spin(0, 255, int(th.cut_bright_thresh))
        self.min_break = self._slider_spin(1, 200, th.min_break_len_px)
        self.band_half = self._slider_spin(1, 30, th.band_halfwidth_px)
        self.gap_merge = self._slider_spin(0, 50, th.gap_merge_px)
        self.edge_guard = self._slider_spin(0, 100, th.edge_guard_px)
        form.addRow("cut_bright_thresh", self.cut_thresh[2])
        form.addRow("min_break_len_px", self.min_break[2])
        form.addRow("band_halfwidth_px", self.band_half[2])
        form.addRow("gap_merge_px", self.gap_merge[2])
        form.addRow("edge_guard_px", self.edge_guard[2])
        root.addWidget(box)

        # ---------------- 參考 Judge ----------------
        box = QGroupBox("參考 Judge（生產以 LabVIEW 為準）")
        form = QFormLayout(box)
        self.judge_max_len = self._dspin(0.0, 1000.0, 0.0, 1.0)
        self.judge_max_n = self._spin(0, 100, 0)
        form.addRow("judge_max_break_px", self.judge_max_len)
        form.addRow("judge_max_breaks", self.judge_max_n)
        root.addWidget(box)
        root.addStretch(1)

        # ---------------- wiring ----------------
        self.roi_mode.currentTextChanged.connect(self._emit_roi)
        for w in (self.roi_left, self.roi_top, self.roi_right, self.roi_bottom):
            w.valueChanged.connect(self._emit_roi)
        self.btn_apply_autoframe.clicked.connect(
            self.applyAutoFrameRequested.emit)
        self.ceramic_min[1].valueChanged.connect(
            lambda v: self.paramsChanged.emit("roi", {"ceramic_min": int(v)}))

        self.angle_search.valueChanged.connect(
            lambda v: self.paramsChanged.emit("angle", {"angle_search_deg": float(v)}))
        self.angle_coarse.valueChanged.connect(
            lambda v: self.paramsChanged.emit("angle", {"angle_coarse_step": float(v)}))
        self.angle_fine.valueChanged.connect(
            lambda v: self.paramsChanged.emit("angle", {"angle_fine_step": float(v)}))
        self.angle_max_side.valueChanged.connect(
            lambda v: self.paramsChanged.emit("angle", {"angle_est_max_side": int(v)}))
        self.angle_tol.valueChanged.connect(
            lambda v: self.paramsChanged.emit("tol", {"angle_tol_deg": float(v)}))

        self.peak_ratio.valueChanged.connect(
            lambda v: self.paramsChanged.emit("lines", {"peak_min_dist_ratio": float(v)}))
        self.ridge_kernel.valueChanged.connect(
            lambda v: self.paramsChanged.emit("lines", {"ridge_kernel_px": int(v)}))

        self.cut_thresh[1].valueChanged.connect(
            lambda v: self.paramsChanged.emit("thresholds", {"cut_bright_thresh": float(v)}))
        self.min_break[1].valueChanged.connect(
            lambda v: self.paramsChanged.emit("thresholds", {"min_break_len_px": int(v)}))
        self.band_half[1].valueChanged.connect(
            lambda v: self.paramsChanged.emit("thresholds", {"band_halfwidth_px": int(v)}))
        self.gap_merge[1].valueChanged.connect(
            lambda v: self.paramsChanged.emit("thresholds", {"gap_merge_px": int(v)}))
        self.edge_guard[1].valueChanged.connect(
            lambda v: self.paramsChanged.emit("thresholds", {"edge_guard_px": int(v)}))

        self.judge_max_len.valueChanged.connect(
            lambda v: self.paramsChanged.emit("judge", {"judge_max_break_px": float(v)}))
        self.judge_max_n.valueChanged.connect(
            lambda v: self.paramsChanged.emit("judge", {"judge_max_breaks": int(v)}))

        self._emit_roi()

    # ---------------- helpers ----------------
    @staticmethod
    def _spin(lo, hi, val):
        s = QSpinBox(); s.setRange(lo, hi); s.setValue(val)
        s.setKeyboardTracking(False)
        return s

    @staticmethod
    def _dspin(lo, hi, val, step):
        s = QDoubleSpinBox(); s.setRange(lo, hi); s.setValue(val)
        s.setSingleStep(step); s.setDecimals(3)
        s.setKeyboardTracking(False)
        return s

    @staticmethod
    def _slider_spin(lo, hi, val):
        """回 (slider, spin, container) —— 滑桿與數字框雙向同步。"""
        slider = QSlider(Qt.Horizontal); slider.setRange(lo, hi); slider.setValue(int(val))
        spin = QSpinBox(); spin.setRange(lo, hi); spin.setValue(int(val))
        spin.setKeyboardTracking(False)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        w = QWidget(); lay = QHBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(slider, 1); lay.addWidget(spin)
        return slider, spin, w

    def _emit_roi(self, *_):
        manual = self.roi_mode.currentText() == "Manual"
        for w in (self.roi_left, self.roi_top, self.roi_right, self.roi_bottom):
            w.setEnabled(manual)
        if manual:
            left, top = self.roi_left.value(), self.roi_top.value()
            right, bottom = self.roi_right.value(), self.roi_bottom.value()
            spec = ve_core.RoiSpec("Manual", ve_core.Rect(
                left, top, max(0, right - left), max(0, bottom - top)))
        else:
            spec = ve_core.RoiSpec("AutoFrame")
        self.roiModeChanged.emit(spec)

    def set_manual_rect(self, rect: "ve_core.Rect"):
        """把 rect（原圖座標）灌入左/上/右/下欄位並切到 Manual 模式。

        供「套用 AutoFrame 結果為 Manual 起點」按鈕使用。
        """
        for w, v in ((self.roi_left, rect.x), (self.roi_top, rect.y),
                     (self.roi_right, rect.x + rect.w),
                     (self.roi_bottom, rect.y + rect.h)):
            w.blockSignals(True)
            w.setValue(v)
            w.blockSignals(False)
        self.roi_mode.setCurrentText("Manual")   # 若模式未變不會觸發訊號
        self._emit_roi()
