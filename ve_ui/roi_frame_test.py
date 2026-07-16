# -*- coding: utf-8 -*-
"""AutoInRoi（操作員粗框 + ve_core/frame.py::find_inner_roi 精確找內緣）
獨立驗證工具。

背景：AutoFrame 對全圖直接掃描在實圖上尚未成功過（黑框在治具遮擋處
會與影像外圍暗背景相連，或影像本身已含旋轉留白，導致掃描過早鎖到
影像邊緣而非真正的大黑框內緣）。這裡驗證新策略：操作員先拖曳一個
粗略 ROI 圈住大黑框，程式只在這個範圍內精確找內緣。

本工具不接 InspectionSession、不跑完整管線；直接呼叫
ve_core.frame.find_inner_roi（裁切子圖 → 找內緣 → 座標平移回原圖），
與 ve_core.pipeline.resolve_roi 的 AutoInRoi 分支做的事完全一致，只是
額外把 frac / run_need / margin 開放給面板即時調整（AlgoConfig 目前
未收這幾個欄位，屬 ARCHITECTURE.md 9 節待辦 4 的既有缺口）。

如實顯示：偵測失敗就顯示失敗原因，不做任何讓畫面「看起來成功」的調包。
find_inner_roi 本身只回軸對齊矩形，不含角度估計，故不顯示角度欄位。

操作：
    1. 載入影像（預設開 testdata/real/，也可手動選檔/選資料夾）
    2. 預設為「畫粗框」模式：在影像上拖曳左鍵圈出大黑框的粗略範圍（綠框）
    3. 放開滑鼠後自動執行 AutoInRoi，黃框疊圖顯示精確內緣，並顯示座標
    4. 右側可即時調整 ceramic_min / frac / run_need / margin，調整後
       用目前的粗框自動重跑
    5. 需要平移影像時，切到「平移」模式（工具列切換）；滾輪縮放兩種
       模式下都可用

啟動：venv\\Scripts\\python -m ve_ui.roi_frame_test [影像路徑或資料夾]
"""
import os
import sys

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
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

_COL_ROUGH = QColor(0, 220, 0)      # 綠：操作員粗框
_COL_INNER = QColor(255, 220, 0)    # 黃：AutoInRoi 精確內緣
_COL_CORNER = QColor(255, 30, 30)   # 紅：角點
_COL_FAIL = QColor(255, 30, 30)     # 紅：失敗提示


class RoiDrawView(QGraphicsView):
    """縮放/平移影像檢視。預設「畫粗框」模式：左鍵拖曳畫綠框，
    放開滑鼠發出 roiDrawn(x, y, w, h)（原圖座標，已裁到影像範圍內）。
    切到平移模式後左鍵拖曳改為 ScrollHandDrag。"""

    roiDrawn = Signal(int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self._pix_item = None
        self._img_ref = None
        self._img_w = 0
        self._img_h = 0

        self._pan_mode = False
        self._dragging = False
        self._drag_start = None
        self._rough_item = None
        self._inner_items = []

        self.setDragMode(QGraphicsView.NoDrag)

    # ------------------------------------------------ image
    def set_image(self, gray: np.ndarray):
        gray = np.ascontiguousarray(gray)
        h, w = gray.shape
        qimg = QImage(gray.data, w, h, w, QImage.Format_Grayscale8)
        self._img_ref = gray
        self._img_w, self._img_h = w, h
        pm = QPixmap.fromImage(qimg)
        if self._pix_item is None:
            self._pix_item = QGraphicsPixmapItem()
            self._pix_item.setZValue(0)
            self._scene.addItem(self._pix_item)
        self._pix_item.setPixmap(pm)
        self._scene.setSceneRect(QRectF(0, 0, w, h))
        self.clear_rough()
        self.clear_inner()
        self.fit()

    def fit(self):
        if self._pix_item is not None:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, ev):
        factor = 1.25 if ev.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)

    # ------------------------------------------------ mode
    def set_pan_mode(self, enabled: bool):
        self._pan_mode = enabled
        self.setDragMode(QGraphicsView.ScrollHandDrag if enabled
                         else QGraphicsView.NoDrag)

    # ------------------------------------------------ 粗框繪製
    def clear_rough(self):
        if self._rough_item is not None:
            self._scene.removeItem(self._rough_item)
            self._rough_item = None

    def clear_inner(self):
        for it in self._inner_items:
            self._scene.removeItem(it)
        self._inner_items = []

    def set_rough_rect(self, x, y, w, h):
        self.clear_rough()
        pen = QPen(_COL_ROUGH, 0)
        pen.setCosmetic(True)
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        self._rough_item = self._scene.addRect(QRectF(x, y, w, h), pen)
        self._rough_item.setZValue(4)

    def mousePressEvent(self, ev):
        if self._pan_mode or self._pix_item is None or ev.button() != Qt.LeftButton:
            super().mousePressEvent(ev)
            return
        self._dragging = True
        self._drag_start = self.mapToScene(ev.position().toPoint())
        self.clear_rough()
        ev.accept()

    def mouseMoveEvent(self, ev):
        if not self._dragging:
            super().mouseMoveEvent(ev)
            return
        cur = self.mapToScene(ev.position().toPoint())
        x = min(self._drag_start.x(), cur.x())
        y = min(self._drag_start.y(), cur.y())
        w = abs(cur.x() - self._drag_start.x())
        h = abs(cur.y() - self._drag_start.y())
        self.set_rough_rect(x, y, w, h)
        ev.accept()

    def mouseReleaseEvent(self, ev):
        if not self._dragging or ev.button() != Qt.LeftButton:
            super().mouseReleaseEvent(ev)
            return
        self._dragging = False
        cur = self.mapToScene(ev.position().toPoint())
        x = min(self._drag_start.x(), cur.x())
        y = min(self._drag_start.y(), cur.y())
        w = abs(cur.x() - self._drag_start.x())
        h = abs(cur.y() - self._drag_start.y())
        # 裁到影像範圍內
        ix = max(0, int(round(x)))
        iy = max(0, int(round(y)))
        iw = int(round(min(x + w, self._img_w) - ix))
        ih = int(round(min(y + h, self._img_h) - iy))
        ev.accept()
        if iw < 20 or ih < 20:
            self.clear_rough()
            return
        self.set_rough_rect(ix, iy, iw, ih)
        self.roiDrawn.emit(ix, iy, iw, ih)

    # ------------------------------------------------ 結果疊圖
    def draw_inner_success(self, x, y, w, h):
        self.clear_inner()
        pen = QPen(_COL_INNER, 0)
        pen.setCosmetic(True)
        pen.setWidth(3)
        rect_item = self._scene.addRect(QRectF(x, y, w, h), pen)
        rect_item.setZValue(5)
        self._inner_items.append(rect_item)

        corner_pen = QPen(_COL_CORNER, 0)
        corner_pen.setCosmetic(True)
        corner_brush = QBrush(_COL_CORNER)
        r = 9.0
        for (cx, cy) in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
            dot = self._scene.addEllipse(cx - r, cy - r, 2 * r, 2 * r,
                                         corner_pen, corner_brush)
            dot.setZValue(6)
            self._inner_items.append(dot)

        font = QFont()
        font.setPointSizeF(15.0)
        font.setBold(True)
        label = self._scene.addSimpleText(
            "AutoInRoi OK  x=%d y=%d w=%d h=%d" % (x, y, w, h), font)
        label.setBrush(QBrush(_COL_INNER))
        label.setPos(QPointF(x, max(0, y - 32)))
        label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations)
        label.setZValue(7)
        self._inner_items.append(label)

    def draw_inner_failure(self, reason: str):
        self.clear_inner()
        font = QFont()
        font.setPointSizeF(17.0)
        font.setBold(True)
        label = self._scene.addSimpleText("AutoInRoi 失敗：%s" % reason, font)
        label.setBrush(QBrush(_COL_FAIL))
        label.setPos(QPointF(20, 20))
        label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations)
        label.setZValue(7)
        self._inner_items.append(label)


class RoiFrameTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoInRoi 驗證工具（粗框 + find_inner_roi，不改演算法）")
        self.resize(1450, 920)

        self._gray = None
        self._current_path = None
        self._rough_rect = None    # (x, y, w, h) 原圖座標

        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        self.view = RoiDrawView()
        self.view.roiDrawn.connect(self._on_rough_drawn)
        splitter.addWidget(self.view)

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
        self.file_list.setMaximumHeight(140)
        rlay.addWidget(self.file_list)

        mode_row = QHBoxLayout()
        self.pan_btn = QPushButton("平移模式（目前：畫粗框）")
        self.pan_btn.setCheckable(True)
        self.pan_btn.toggled.connect(self._on_pan_toggled)
        btn_clear_rough = QPushButton("清除粗框")
        btn_clear_rough.clicked.connect(self._clear_rough)
        mode_row.addWidget(self.pan_btn)
        mode_row.addWidget(btn_clear_rough)
        rlay.addLayout(mode_row)
        rlay.addWidget(QLabel(
            "操作：預設「畫粗框」模式，左鍵拖曳圈出大黑框粗略範圍（綠框，"
            "放開滑鼠即自動執行）；需要平移畫面時點「平移模式」。"))

        box = QGroupBox("find_inner_roi 參數（在粗框子圖內執行）")
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

        btn_rerun = QPushButton("用目前粗框重新執行")
        btn_rerun.clicked.connect(self._run_auto_in_roi)
        rlay.addWidget(btn_rerun)

        rlay.addWidget(QLabel("結果："))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(220)
        rlay.addWidget(self.result_text)

        rlay.addStretch(1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(150)
        self._debounce.timeout.connect(self._run_auto_in_roi)

        if os.path.isdir(_DEFAULT_FOLDER):
            self._populate_folder(_DEFAULT_FOLDER)

    # ---------------------------------------------------------- 模式
    def _on_pan_toggled(self, checked):
        self.view.set_pan_mode(checked)
        self.pan_btn.setText("平移模式（目前：%s）"
                             % ("平移" if checked else "畫粗框"))

    def _clear_rough(self):
        self.view.clear_rough()
        self.view.clear_inner()
        self._rough_rect = None
        self.result_text.setPlainText("尚未畫粗框。")

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
        self._rough_rect = None
        self.view.set_image(gray)
        self.setWindowTitle("AutoInRoi 驗證工具 — %s" % os.path.basename(path))
        self.result_text.setPlainText(
            "已載入 %s（%d x %d）。請在影像上拖曳左鍵圈出大黑框粗略範圍。"
            % (path, gray.shape[1], gray.shape[0]))

    # ---------------------------------------------------------- 執行
    def _on_rough_drawn(self, x, y, w, h):
        self._rough_rect = (x, y, w, h)
        self._run_auto_in_roi()

    def _schedule_rerun(self, *_):
        if self._rough_rect is not None:
            self._debounce.start()

    def _run_auto_in_roi(self):
        if self._gray is None or self._rough_rect is None:
            return
        rx, ry, rw, rh = self._rough_rect
        ceramic_min = self.ceramic_min.value()
        frac = self.frac.value()
        run_need = self.run_need.value()
        margin = self.margin.value()

        ih_img, iw_img = self._gray.shape
        sub = self._gray[ry:ry + rh, rx:rx + rw]

        try:
            fx, fy, fw, fh = frame_mod.find_inner_roi(
                sub, ceramic_min=ceramic_min, frac=frac,
                run_need=run_need, margin=margin)
        except FrameNotFound as e:
            self.view.draw_inner_failure(str(e))
            self.result_text.setPlainText(
                "檔案：%s\n"
                "狀態：失敗（FrameNotFound）\n"
                "原因：%s\n"
                "粗框（原圖座標）：x=%d y=%d w=%d h=%d\n"
                "參數：ceramic_min=%d frac=%.3f run_need=%d margin=%d\n"
                "角度：find_inner_roi 不估角度，此欄位不適用"
                % (self._current_path, str(e), rx, ry, rw, rh,
                   ceramic_min, frac, run_need, margin))
            return

        x, y = fx + rx, fy + ry
        w, h = fw, fh
        self.view.draw_inner_success(x, y, w, h)
        self.result_text.setPlainText(
            "檔案：%s\n"
            "狀態：成功\n"
            "內緣 ROI（原圖座標）：x=%d y=%d w=%d h=%d\n"
            "右下角：(%d, %d)\n"
            "粗框（原圖座標）：x=%d y=%d w=%d h=%d\n"
            "內緣佔粗框比例：寬 %.1f%%　高 %.1f%%\n"
            "影像尺寸：%d x %d\n"
            "參數：ceramic_min=%d frac=%.3f run_need=%d margin=%d\n"
            "角度：find_inner_roi 不估角度，此欄位不適用"
            % (self._current_path, x, y, w, h, x + w, y + h,
               rx, ry, rw, rh, 100.0 * w / rw, 100.0 * h / rh,
               iw_img, ih_img, ceramic_min, frac, run_need, margin))


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    win = RoiFrameTestWindow()
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
