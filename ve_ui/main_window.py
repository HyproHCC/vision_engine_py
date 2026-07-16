# -*- coding: utf-8 -*-
"""調機工具主視窗。

佈局：中央影像檢視、右側參數 dock、下方結果 dock。
工具列：載圖 / 批次 / 模式切換 / 教導接受 / taught 存取 / 匯出 / 圖層開關。

重算策略：參數變動 → 150ms debounce → 從 dirty 階段重跑。
門檻滑桿只重算 breaks（毫秒級，體感即時）；上游參數會有秒級等待
（狀態列顯示忙碌），調機工具可接受。批次在 QThread 跑不凍 UI。
"""
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QDockWidget, QFileDialog,
                               QLabel, QMainWindow, QMessageBox,
                               QProgressBar, QToolBar, QComboBox)

import ve_core

from .batch import BatchRunner
from .export import (export_batch_csv, export_batch_json,
                     export_defects_csv, export_single_json,
                     load_taught_json, save_taught_json)
from .image_view import ImageView
from .loader import list_images, load_gray
from .param_panel import ParamPanel
from .results_panel import ResultsPanel
from .session import InspectionSession

_MODE_LABELS = [("檢測（發現式）", "discovery"),
                ("檢測（驗證式 taught）", "taught"),
                ("教導", "teach")]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisionEngine 調機工具 (ve_ui)")
        self.resize(1500, 950)

        self.session = InspectionSession()
        self.last_result = None
        self.batch_rows = []
        self.batch_defects = []
        self._batch = None
        self._pending_teach = None       # 教導結果等待「接受」

        # ---- central & docks ----
        self.view = ImageView(self)
        self.setCentralWidget(self.view)

        self.params = ParamPanel(self)
        dock = QDockWidget("參數", self)
        dock.setWidget(self.params)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.results = ResultsPanel(self)
        rdock = QDockWidget("結果", self)
        rdock.setWidget(self.results)
        rdock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.BottomDockWidgetArea, rdock)

        # ---- toolbar ----
        tb = QToolBar("main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        act_open = QAction("載入影像", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.open_image)
        tb.addAction(act_open)

        act_batch = QAction("批次資料夾", self)
        act_batch.triggered.connect(self.run_batch)
        tb.addAction(act_batch)
        tb.addSeparator()

        self.mode_combo = QComboBox()
        for label, _ in _MODE_LABELS:
            self.mode_combo.addItem(label)
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        tb.addWidget(QLabel(" 模式："))
        tb.addWidget(self.mode_combo)

        self.act_accept = QAction("接受教導→存檔", self)
        self.act_accept.setEnabled(False)
        self.act_accept.triggered.connect(self.accept_teach)
        tb.addAction(self.act_accept)

        act_load_tp = QAction("載入 taught", self)
        act_load_tp.triggered.connect(self.load_taught)
        tb.addAction(act_load_tp)
        tb.addSeparator()

        act_export = QAction("匯出結果", self)
        act_export.triggered.connect(self.export_current)
        tb.addAction(act_export)

        act_fit = QAction("適應視窗", self)
        act_fit.triggered.connect(self.view.fit)
        tb.addAction(act_fit)
        tb.addSeparator()

        self.act_draw_roi = QAction("手動畫框（拖曳左鍵）", self, checkable=True)
        self.act_draw_roi.toggled.connect(self._on_draw_roi_toggled)
        tb.addAction(self.act_draw_roi)
        tb.addSeparator()

        # 圖層開關
        self._layer_actions = {}
        for name, label in (("roi", "ROI"), ("lines", "切割線"),
                            ("defects", "斷點"), ("placement", "放置")):
            a = QAction(label, self, checkable=True, checked=True)
            a.toggled.connect(lambda on, n=name:
                              self.view.set_layer_visible(n, on))
            tb.addAction(a)
            self._layer_actions[name] = a

        # ---- status bar ----
        self.lbl_status = QLabel("載入影像開始")
        self.statusBar().addWidget(self.lbl_status, 1)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(220)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.progress)
        self.lbl_taught = QLabel("taught: 無")
        self.statusBar().addPermanentWidget(self.lbl_taught)

        # ---- debounce timer ----
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(150)
        self._debounce.timeout.connect(self.recompute)

        self.params.paramsChanged.connect(self._on_params)
        self.params.roiModeChanged.connect(self._on_roi)
        self.params.applyAutoFrameRequested.connect(self._apply_autoframe_roi)
        self.view.roiDrawn.connect(self._on_roi_drawn)

    # ------------------------------------------------ param plumbing
    def _on_params(self, group: str, kw: dict):
        if group == "judge":
            self.session.update_judge(**kw)
        elif group == "tol":
            self.session.set_angle_tol(kw["angle_tol_deg"])
        else:
            self.session.update_params(group, **kw)
        self._debounce.start()

    def _on_roi(self, spec):
        self.session.set_roi(spec)
        self._debounce.start()

    def _apply_autoframe_roi(self):
        if self.session.gray is None:
            self.lbl_status.setText("尚未載入影像，無法套用 AutoFrame")
            return
        self.lbl_status.setText("AutoFrame 計算中…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            rect = ve_core.resolve_roi(
                self.session.gray, ve_core.RoiSpec("AutoFrame"),
                self.session.cfg)
        except ve_core.FrameNotFound as e:
            self.lbl_status.setText("AutoFrame 找框失敗：%s" % e)
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.params.set_manual_rect(rect)
        self.view.draw_roi(rect)
        self.lbl_status.setText("已將 AutoFrame 結果套用為 Manual ROI 起點")

    def _on_draw_roi_toggled(self, checked):
        self.view.set_draw_roi_mode(checked)

    def _on_roi_drawn(self, x, y, w, h):
        self.params.set_manual_rect(ve_core.Rect(x, y, w, h))
        self.lbl_status.setText(
            "已用拖曳框套用為 Manual ROI（x=%d y=%d w=%d h=%d）" % (x, y, w, h))

    def _mode_changed(self, idx: int):
        mode = _MODE_LABELS[idx][1]
        if mode == "taught" and self.session.taught is None:
            self.lbl_status.setText("尚無 taught 參數：先教導或載入 taught JSON")
        self.session.set_mode(mode)
        self.act_accept.setEnabled(False)
        self._debounce.start()

    # ------------------------------------------------ actions
    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "載入影像", "",
            "影像 (*.png *.bmp *.jpg *.jpeg *.tif *.tiff)")
        if not path:
            return
        try:
            gray = load_gray(path)
        except IOError as e:
            QMessageBox.warning(self, "載入失敗", str(e))
            return
        self.session.set_image(gray, path)
        self.view.set_image(gray)
        self.view.clear_overlays()
        self.setWindowTitle("VisionEngine 調機工具 — %s"
                            % os.path.basename(path))
        self.recompute()

    def recompute(self):
        if self.session.gray is None:
            return
        self.lbl_status.setText("計算中…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            r = self.session.run()
        finally:
            QApplication.restoreOverrideCursor()
        self.last_result = r
        self.results.show_result(r)
        self._draw(r)
        if r.ok and self.session.mode == "teach" and r.taught is not None:
            self._pending_teach = r.taught
            self.act_accept.setEnabled(True)
            self.lbl_status.setText(
                "教導結果已疊圖 — 目視確認後按「接受教導→存檔」")
        else:
            self._pending_teach = None
            self.act_accept.setEnabled(False)
            self.lbl_status.setText(r.message if not r.ok else
                                    "%s（%.0f ms）" % (r.verdict, r.total_ms))

    def _draw(self, r):
        self.view.clear_overlays()
        if not r.ok:
            if r.roi_rect is not None:
                self.view.draw_roi(r.roi_rect)
            return
        self.view.draw_roi(r.roi_rect)
        if r.placement:
            self.view.draw_placement(r.roi_rect, r.angle_deg,
                                     self.session.angle_tol_deg)
            return
        self.view.draw_lines(r.families)
        if r.defects:
            self.view.draw_defects(r.defects)
        # 重新套用圖層開關狀態
        for name, act in self._layer_actions.items():
            self.view.set_layer_visible(name, act.isChecked())

    def accept_teach(self):
        if self._pending_teach is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "儲存 taught 參數（生產格式）", "taught_params.json",
            "JSON (*.json)")
        if not path:
            return
        try:
            save_taught_json(path, self._pending_teach)
        except OSError as e:
            QMessageBox.warning(self, "存檔失敗", str(e))
            return
        self.session.set_taught(self._pending_teach)
        self.lbl_taught.setText("taught: %s" % os.path.basename(path))
        # 教導接受後自動切到驗證式檢測
        self.mode_combo.setCurrentIndex(1)
        self.lbl_status.setText("taught 已存檔並套用，已切換驗證式檢測")

    def load_taught(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "載入 taught 參數", "", "JSON (*.json)")
        if not path:
            return
        try:
            tp = load_taught_json(path)
        except (OSError, ve_core.TaughtParamsError, ValueError) as e:
            QMessageBox.warning(self, "載入失敗", str(e))
            return
        self.session.set_taught(tp)
        self.lbl_taught.setText("taught: %s" % os.path.basename(path))
        self.mode_combo.setCurrentIndex(1)

    # ------------------------------------------------ batch
    def run_batch(self):
        if self._batch is not None and self._batch.isRunning():
            self._batch.abort()
            self.lbl_status.setText("批次中止中…")
            return
        folder = QFileDialog.getExistingDirectory(self, "批次資料夾")
        if not folder:
            return
        paths = list_images(folder)
        if not paths:
            QMessageBox.information(self, "批次", "資料夾內沒有影像檔")
            return
        mode = self.session.mode if self.session.mode != "teach" \
            else "discovery"
        self._batch = BatchRunner(
            paths, self.session.cfg, self.session.thresholds,
            self.session.judge, self.session.roi,
            self.session.angle_tol_deg, mode, self.session.taught, self)
        self._batch.progress.connect(self._batch_progress)
        self._batch.finishedRows.connect(self._batch_done)
        self.progress.setRange(0, len(paths))
        self.progress.setValue(0)
        self.progress.show()
        self.lbl_status.setText("批次執行中（%d 張）… 再按一次「批次資料夾」可中止"
                                % len(paths))
        self._batch.start()

    def _batch_progress(self, done, total, path):
        self.progress.setValue(done)
        self.lbl_status.setText("批次 %d/%d：%s"
                                % (done, total, os.path.basename(path)))

    def _batch_done(self, rows, defect_rows):
        self.progress.hide()
        self.batch_rows = rows
        self.batch_defects = defect_rows
        n_ng = sum(1 for r in rows if r["verdict"] == "NG")
        n_err = sum(1 for r in rows if r["verdict"] == "SystemError")
        self.lbl_status.setText(
            "批次完成：%d 張，NG %d、SystemError %d — 用「匯出結果」存報表"
            % (len(rows), n_ng, n_err))

    # ------------------------------------------------ export
    def export_current(self):
        if self.batch_rows:
            base, _ = QFileDialog.getSaveFileName(
                self, "匯出批次報表（自動加 _images.csv/_defects.csv/.json）",
                "batch_report", "報表 (*.json)")
            if not base:
                return
            stem = base[:-5] if base.endswith(".json") else base
            try:
                export_batch_json(stem + ".json", self.batch_rows,
                                  self.batch_defects, self.session.cfg,
                                  self.session.thresholds, self.session.judge,
                                  self.session.roi,
                                  self.session.angle_tol_deg,
                                  self.session.mode)
                export_batch_csv(stem + "_images.csv", self.batch_rows)
                export_defects_csv(stem + "_defects.csv", self.batch_defects)
            except OSError as e:
                QMessageBox.warning(self, "匯出失敗", str(e))
                return
            self.lbl_status.setText("批次報表已匯出：%s(.json/_images.csv/"
                                    "_defects.csv)" % os.path.basename(stem))
            return
        if self.last_result is None:
            QMessageBox.information(self, "匯出", "尚無結果可匯出")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "匯出單張結果+參數", "result.json", "JSON (*.json)")
        if not path:
            return
        try:
            export_single_json(path, self.last_result,
                               self.session.image_path, self.session.cfg,
                               self.session.thresholds, self.session.judge,
                               self.session.roi, self.session.angle_tol_deg,
                               self.session.mode)
        except OSError as e:
            QMessageBox.warning(self, "匯出失敗", str(e))
            return
        self.lbl_status.setText("已匯出：%s" % os.path.basename(path))
