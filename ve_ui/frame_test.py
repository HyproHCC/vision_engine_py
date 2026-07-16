# -*- coding: utf-8 -*-
"""AutoFrame（ve_core/frame.py::find_inner_roi）獨立驗證工具。

不接 InspectionSession、不跑完整管線，只做一件事：載圖 → 呼叫
find_inner_roi → 疊圖顯示結果。用於「AutoFrame 在實圖上抓不抓得到框」
的目視驗證，不代表已重新啟動 AutoFrame（見 ARCHITECTURE.md 1.5、
9 節「暫緩區」——AutoFrame 目前為非核心、暫緩狀態，此工具只做現況檢查）。

如實顯示：偵測失敗就顯示失敗原因，不做任何讓畫面「看起來成功」的調包。
AutoFrame（find_inner_roi）本身只回軸對齊矩形，不含角度估計，故不顯示角度欄位。

啟動：venv\\Scripts\\python -m ve_ui.frame_test [影像路徑或資料夾]
"""
import os
import sys

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QGraphicsPixmapItem,
                               QGraphicsScene, QGraphicsView, QGroupBox,
                               QHBoxLayout, QLabel, QListWidget, QMainWindow,
                               QMessageBox, QPushButton, QSpinBox, QSplitter,
                               QTextEdit, QVBoxLayout, QWidget)

from ve_core import frame as frame_mod
from ve_core.errors import FrameNotFound

from .loader import list_images, load_gray

_DEFAULT_FOLDER = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "testdata", "real"))

_COL_OK = QColor(255, 120, 0)      # 橙：AutoFrame 成功框
_COL_CORNER = QColor(255, 30, 30)  # 紅：角點
_COL_FAIL = QColor(255, 30, 30)    # 紅：失敗提示


class FrameView(QGraphicsView):
    """最小可用的縮放/平移影像檢視 + AutoFrame 疊圖（原圖座標）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self._pix_item = None
        self._img_ref = None
        self._overlay_items = []
        self._fitted = False

    def set_image(self, gray):
        gray = np.ascontiguousarray(gray)
        h, w = gray.shape
        qimg = QImage(gray.data, w, h, w, QImage.Format_Grayscale8)
        self._img_ref = gray
        pm = QPixmap.fromImage(qimg)
        if self._pix_item is None:
            self._pix_item = QGraphicsPixmapItem()
            self._pix_item.setZValue(0)
            self._scene.addItem(self._pix_item)
        self._pix_item.setPixmap(pm)
        self._scene.setSceneRect(QRectF(0, 0, w, h))
        self._fitted = False
        self.fit()

    def fit(self):
        if self._pix_item is not None:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
            self._fitted = True

    def wheelEvent(self, ev):
        factor = 1.25 if ev.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)

    def clear_overlay(self):
        for it in self._overlay_items:
            self._scene.removeItem(it)
        self._overlay_items = []

    def draw_success(self, x, y, w, h):
        self.clear_overlay()
        pen = QPen(_COL_OK, 0)
        pen.setCosmetic(True)
        pen.setWidth(3)
        rect_item = self._scene.addRect(QRectF(x, y, w, h), pen)
        rect_item.setZValue(5)
        self._overlay_items.append(rect_item)

        corner_pen = QPen(_COL_CORNER, 0)
        corner_pen.setCosmetic(True)
        corner_brush = QBrush(_COL_CORNER)
        r = 10.0
        for (cx, cy) in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
            dot = self._scene.addEllipse(cx - r, cy - r, 2 * r, 2 * r,
                                         corner_pen, corner_brush)
            dot.setZValue(6)
            self._overlay_items.append(dot)

        font = QFont()
        font.setPointSizeF(16.0)
        font.setBold(True)
        label = self._scene.addSimpleText(
            "AutoFrame OK  x=%d y=%d w=%d h=%d" % (x, y, w, h), font)
        label.setBrush(QBrush(_COL_OK))
        label.setPos(QPointF(x, max(0, y - 34)))
        label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations)
        label.setZValue(7)
        self._overlay_items.append(label)

    def draw_failure(self, reason: str):
        self.clear_overlay()
        font = QFont()
        font.setPointSizeF(18.0)
        font.setBold(True)
        label = self._scene.addSimpleText("AutoFrame 失敗：%s" % reason, font)
        label.setBrush(QBrush(_COL_FAIL))
        label.setPos(QPointF(20, 20))
        label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations)
        label.setZValue(7)
        self._overlay_items.append(label)


class FrameTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoFrame 驗證工具（ve_core/frame.py，不改演算法）")
        self.resize(1400, 900)

        self._gray = None
        self._current_path = None

        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # ---------------- 左：影像檢視 ----------------
        self.view = FrameView()
        splitter.addWidget(self.view)

        # ---------------- 右：控制面板 ----------------
        right = QWidget()
        rlay = QVBoxLayout(right)

        open_row = QHBoxLayout()
        btn_file = QPushButton("開啟影像…")
        btn_folder = QPushButton("開啟資料夾…")
        btn_fit = QPushButton("Fit")
        btn_file.clicked.connect(self._open_file_dialog)
        btn_folder.clicked.connect(self._open_folder_dialog)
        btn_fit.clicked.connect(self.view.fit)
        open_row.addWidget(btn_file)
        open_row.addWidget(btn_folder)
        open_row.addWidget(btn_fit)
        rlay.addLayout(open_row)

        rlay.addWidget(QLabel("資料夾內影像："))
        self.file_list = QListWidget()
        self.file_list.currentTextChanged.connect(self._on_pick_file)
        self.file_list.setMaximumHeight(160)
        rlay.addWidget(self.file_list)

        box = QGroupBox("find_inner_roi 參數")
        form = QFormLayout(box)
        self.ceramic_min = QSpinBox()
        self.ceramic_min.setRange(0, 255)
        self.ceramic_min.setValue(90)
        self.ceramic_min.setKeyboardTracking(False)
        form.addRow("ceramic_min", self.ceramic_min)

        self.frac = QDoubleSpinBox()
        self.frac.setRange(0.0, 1.0)
        self.frac.setDecimals(3)
        self.frac.setSingleStep(0.01)
        self.frac.setValue(0.05)
        self.frac.setKeyboardTracking(False)
        form.addRow("frac", self.frac)

        self.run_need = QSpinBox()
        self.run_need.setRange(1, 500)
        self.run_need.setValue(12)
        self.run_need.setKeyboardTracking(False)
        form.addRow("run_need", self.run_need)

        self.margin = QSpinBox()
        self.margin.setRange(0, 200)
        self.margin.setValue(4)
        self.margin.setKeyboardTracking(False)
        form.addRow("margin", self.margin)
        rlay.addWidget(box)

        for w in (self.ceramic_min, self.frac, self.run_need, self.margin):
            w.valueChanged.connect(self._schedule_rerun)

        btn_rerun = QPushButton("重新執行 AutoFrame")
        btn_rerun.clicked.connect(self._run_autoframe)
        rlay.addWidget(btn_rerun)

        rlay.addWidget(QLabel("結果："))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(200)
        rlay.addWidget(self.result_text)

        rlay.addWidget(QLabel("四張 testdata/real 批次摘要："))
        self.batch_text = QTextEdit()
        self.batch_text.setReadOnly(True)
        rlay.addWidget(self.batch_text)
        btn_batch = QPushButton("跑 testdata/real 四張批次驗證")
        btn_batch.clicked.connect(self._run_batch)
        rlay.addWidget(btn_batch)

        rlay.addStretch(1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(150)
        self._debounce.timeout.connect(self._run_autoframe)

        if os.path.isdir(_DEFAULT_FOLDER):
            self._populate_folder(_DEFAULT_FOLDER)

    # ---------------------------------------------------------- 開檔
    def _open_file_dialog(self):
        start = _DEFAULT_FOLDER if os.path.isdir(_DEFAULT_FOLDER) else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "開啟影像", start,
            "Images (*.png *.bmp *.jpg *.jpeg *.tif *.tiff)")
        if path:
            self._load_path(path)

    def _open_folder_dialog(self):
        start = _DEFAULT_FOLDER if os.path.isdir(_DEFAULT_FOLDER) else ""
        folder = QFileDialog.getExistingDirectory(self, "開啟資料夾", start)
        if folder:
            self._populate_folder(folder)

    def _populate_folder(self, folder):
        self.file_list.blockSignals(True)
        self.file_list.clear()
        paths = list_images(folder)
        self._folder_paths = {os.path.basename(p): p for p in paths}
        for name in self._folder_paths:
            self.file_list.addItem(name)
        self.file_list.blockSignals(False)
        if paths:
            self.file_list.setCurrentRow(0)
            self._load_path(paths[0])

    def _on_pick_file(self, name):
        if name and name in getattr(self, "_folder_paths", {}):
            self._load_path(self._folder_paths[name])

    def _load_path(self, path):
        try:
            gray = load_gray(path)
        except IOError as e:
            QMessageBox.warning(self, "載入失敗", str(e))
            return
        self._gray = gray
        self._current_path = path
        self.view.set_image(gray)
        self.setWindowTitle("AutoFrame 驗證工具 — %s" % os.path.basename(path))
        self._run_autoframe()

    # ---------------------------------------------------------- 執行
    def _schedule_rerun(self, *_):
        self._debounce.start()

    def _run_autoframe(self):
        if self._gray is None:
            return
        ceramic_min = self.ceramic_min.value()
        frac = self.frac.value()
        run_need = self.run_need.value()
        margin = self.margin.value()
        try:
            x, y, w, h = frame_mod.find_inner_roi(
                self._gray, ceramic_min=ceramic_min, frac=frac,
                run_need=run_need, margin=margin)
        except FrameNotFound as e:
            self.view.draw_failure(str(e))
            self.result_text.setPlainText(
                "檔案：%s\n"
                "狀態：失敗（FrameNotFound）\n"
                "原因：%s\n"
                "參數：ceramic_min=%d frac=%.3f run_need=%d margin=%d\n"
                "角度：AutoFrame（find_inner_roi）不估角度，此欄位不適用"
                % (self._current_path, str(e), ceramic_min, frac, run_need,
                   margin))
            return
        ih, iw = self._gray.shape
        self.view.draw_success(x, y, w, h)
        self.result_text.setPlainText(
            "檔案：%s\n"
            "狀態：成功\n"
            "ROI（原圖座標）：x=%d y=%d w=%d h=%d\n"
            "右下角：(%d, %d)\n"
            "影像尺寸：%d x %d\n"
            "ROI 佔比：寬 %.1f%%　高 %.1f%%\n"
            "參數：ceramic_min=%d frac=%.3f run_need=%d margin=%d\n"
            "角度：AutoFrame（find_inner_roi）不估角度，此欄位不適用"
            % (self._current_path, x, y, w, h, x + w, y + h, iw, ih,
               100.0 * w / iw, 100.0 * h / ih,
               ceramic_min, frac, run_need, margin))

    def _run_batch(self):
        if not os.path.isdir(_DEFAULT_FOLDER):
            self.batch_text.setPlainText("找不到 testdata/real 資料夾：%s"
                                         % _DEFAULT_FOLDER)
            return
        ceramic_min = self.ceramic_min.value()
        frac = self.frac.value()
        run_need = self.run_need.value()
        margin = self.margin.value()
        lines = []
        for path in list_images(_DEFAULT_FOLDER):
            name = os.path.basename(path)
            try:
                gray = load_gray(path)
            except IOError as e:
                lines.append("%s: 載入失敗 - %s" % (name, e))
                continue
            ih, iw = gray.shape
            try:
                x, y, w, h = frame_mod.find_inner_roi(
                    gray, ceramic_min=ceramic_min, frac=frac,
                    run_need=run_need, margin=margin)
            except FrameNotFound as e:
                lines.append("%s: 失敗 - %s" % (name, e))
                continue
            lines.append(
                "%s: OK  x=%d y=%d w=%d h=%d  (影像 %dx%d, 佔比 %.1f%% x %.1f%%)"
                % (name, x, y, w, h, iw, ih, 100.0 * w / iw, 100.0 * h / ih))
        self.batch_text.setPlainText("\n".join(lines))


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    win = FrameTestWindow()
    win.show()
    if len(argv) > 1:
        target = argv[1]
        if os.path.isdir(target):
            win._populate_folder(target)
        elif os.path.isfile(target):
            win._load_path(target)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
