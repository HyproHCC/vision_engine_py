# -*- coding: utf-8 -*-
"""影像檢視：縮放/平移 + 多層 overlay（皆為原圖座標，零自寫換算）。

圖層：
    roi        藍框（估角用 ROI）
    lines      綠線（找到的切割線）
    defects    紅段 + 端點圓 + line_id 編號
    placement  黃框 + 放置異常提示
    teach      教導結果疊圖（沿用 lines 圖層 + 資訊文字）

畫框模式（set_draw_roi_mode）：左鍵拖曳畫綠色虛線框，放開滑鼠發出
roiDrawn(x, y, w, h)（原圖座標，已裁到影像範圍內）；沿用
ve_ui/roi_frame_test.py 的手勢邏輯。平移模式（預設）維持原本
ScrollHandDrag 行為不變。
"""
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QImage, QPainter, QPen,
                           QPixmap)
from PySide6.QtWidgets import (QGraphicsItemGroup, QGraphicsPixmapItem,
                               QGraphicsScene, QGraphicsView)

_COL_ROI = QColor(70, 130, 240)
_COL_LINE = QColor(0, 200, 90)
_COL_DEFECT = QColor(235, 40, 40)
_COL_PLACEMENT = QColor(240, 190, 0)
_COL_ROI_DRAW = QColor(0, 220, 0)

LAYERS = ("roi", "lines", "defects", "placement")


class ImageView(QGraphicsView):
    roiDrawn = Signal(int, int, int, int)   # x, y, w, h（原圖座標）

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
        self._img_ref = None            # 防 QImage 底層 buffer 被 GC
        self._img_w = 0
        self._img_h = 0
        self._groups = {}
        self._fitted = False

        self._draw_roi_mode = False
        self._dragging_roi = False
        self._roi_drag_start = None
        self._roi_draw_item = None

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
        self._clear_roi_draw()
        if not self._fitted:
            self.fit()
            self._fitted = True

    def fit(self):
        if self._pix_item is not None:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, ev):
        factor = 1.25 if ev.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)

    # ------------------------------------------------ 手動畫框模式
    def set_draw_roi_mode(self, enabled: bool):
        self._draw_roi_mode = enabled
        self._clear_roi_draw()
        self.setDragMode(QGraphicsView.NoDrag if enabled
                         else QGraphicsView.ScrollHandDrag)

    def _clear_roi_draw(self):
        if self._roi_draw_item is not None:
            self._scene.removeItem(self._roi_draw_item)
            self._roi_draw_item = None

    def _set_roi_draw_rect(self, x, y, w, h):
        self._clear_roi_draw()
        pen = QPen(_COL_ROI_DRAW, 0)
        pen.setCosmetic(True)
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        self._roi_draw_item = self._scene.addRect(QRectF(x, y, w, h), pen)
        self._roi_draw_item.setZValue(10)

    def mousePressEvent(self, ev):
        if (not self._draw_roi_mode or self._pix_item is None
                or ev.button() != Qt.LeftButton):
            super().mousePressEvent(ev)
            return
        self._dragging_roi = True
        self._roi_drag_start = self.mapToScene(ev.position().toPoint())
        self._clear_roi_draw()
        ev.accept()

    def mouseMoveEvent(self, ev):
        if not self._dragging_roi:
            super().mouseMoveEvent(ev)
            return
        cur = self.mapToScene(ev.position().toPoint())
        x = min(self._roi_drag_start.x(), cur.x())
        y = min(self._roi_drag_start.y(), cur.y())
        w = abs(cur.x() - self._roi_drag_start.x())
        h = abs(cur.y() - self._roi_drag_start.y())
        self._set_roi_draw_rect(x, y, w, h)
        ev.accept()

    def mouseReleaseEvent(self, ev):
        if not self._dragging_roi or ev.button() != Qt.LeftButton:
            super().mouseReleaseEvent(ev)
            return
        self._dragging_roi = False
        cur = self.mapToScene(ev.position().toPoint())
        x = min(self._roi_drag_start.x(), cur.x())
        y = min(self._roi_drag_start.y(), cur.y())
        w = abs(cur.x() - self._roi_drag_start.x())
        h = abs(cur.y() - self._roi_drag_start.y())
        # 裁到影像範圍內
        ix = max(0, int(round(x)))
        iy = max(0, int(round(y)))
        iw = int(round(min(x + w, self._img_w) - ix))
        ih = int(round(min(y + h, self._img_h) - iy))
        ev.accept()
        if iw < 20 or ih < 20:
            self._clear_roi_draw()
            return
        self._set_roi_draw_rect(ix, iy, iw, ih)
        self.roiDrawn.emit(ix, iy, iw, ih)

    # ------------------------------------------------ overlays
    def _group(self, name: str) -> QGraphicsItemGroup:
        g = self._groups.get(name)
        if g is None:
            g = QGraphicsItemGroup()
            g.setZValue({"roi": 1, "lines": 2, "defects": 3,
                         "placement": 4}[name])
            self._scene.addItem(g)
            self._groups[name] = g
        return g

    def clear_layer(self, name: str):
        g = self._groups.pop(name, None)
        if g is not None:
            self._scene.removeItem(g)

    def clear_overlays(self):
        for name in list(self._groups):
            self.clear_layer(name)
        self._clear_roi_draw()

    def set_layer_visible(self, name: str, visible: bool):
        g = self._groups.get(name)
        if g is not None:
            g.setVisible(visible)

    def draw_roi(self, rect):
        self.clear_layer("roi")
        if rect is None:
            return
        g = self._group("roi")
        pen = QPen(_COL_ROI, 0)           # cosmetic：線寬不隨 zoom
        pen.setCosmetic(True)
        pen.setWidth(2)
        r = self._scene.addRect(QRectF(rect.x, rect.y, rect.w, rect.h), pen)
        g.addToGroup(r)

    def draw_lines(self, families):
        """families: [FamilyView]，segments 為原圖座標。"""
        self.clear_layer("lines")
        g = self._group("lines")
        pen = QPen(_COL_LINE, 0)
        pen.setCosmetic(True)
        pen.setWidth(1)
        for fam in families:
            for (p1, p2) in fam.segments:
                item = self._scene.addLine(p1[0], p1[1], p2[0], p2[1], pen)
                g.addToGroup(item)

    def draw_defects(self, defects, px_scale_hint: float = 1.0):
        """defects: [BreakDefect] 原圖座標。紅段 + 端點圓 + 編號。"""
        self.clear_layer("defects")
        g = self._group("defects")
        pen = QPen(_COL_DEFECT, 0)
        pen.setCosmetic(True)
        pen.setWidth(3)
        dot_pen = QPen(_COL_DEFECT, 0)
        dot_pen.setCosmetic(True)
        brush = QBrush(_COL_DEFECT)
        font = QFont()
        font.setPointSizeF(11.0)
        r = 6.0 * px_scale_hint
        for i, d in enumerate(defects, 1):
            seg = self._scene.addLine(d.x1, d.y1, d.x2, d.y2, pen)
            g.addToGroup(seg)
            for (x, y) in ((d.x1, d.y1), (d.x2, d.y2)):
                dot = self._scene.addEllipse(x - r, y - r, 2 * r, 2 * r,
                                             dot_pen, brush)
                g.addToGroup(dot)
            label = self._scene.addSimpleText("#%d L%d %.0fpx"
                                              % (i, d.line_id, d.length_px),
                                              font)
            label.setBrush(QBrush(_COL_DEFECT))
            label.setPos(QPointF(min(d.x1, d.x2) + 8, min(d.y1, d.y2) - 28))
            # 讓文字大小不隨 zoom 縮到看不見
            label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations)
            g.addToGroup(label)

    def draw_placement(self, roi_rect, angle_deg: float, tol: float):
        self.clear_layer("placement")
        g = self._group("placement")
        pen = QPen(_COL_PLACEMENT, 0)
        pen.setCosmetic(True)
        pen.setWidth(4)
        if roi_rect is not None:
            r = self._scene.addRect(QRectF(roi_rect.x, roi_rect.y,
                                           roi_rect.w, roi_rect.h), pen)
            g.addToGroup(r)
        font = QFont()
        font.setPointSizeF(16.0)
        font.setBold(True)
        t = self._scene.addSimpleText(
            "放置異常  angle=%.2f°  (tol=%.1f°)" % (angle_deg, tol), font)
        t.setBrush(QBrush(_COL_PLACEMENT))
        x0 = roi_rect.x if roi_rect else 20
        y0 = (roi_rect.y - 40) if roi_rect else 20
        t.setPos(QPointF(x0, max(4, y0)))
        t.setFlag(t.GraphicsItemFlag.ItemIgnoresTransformations)
        g.addToGroup(t)
