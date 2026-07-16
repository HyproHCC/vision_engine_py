# -*- coding: utf-8 -*-
"""結果面板：斷點表格 + 線族摘要 + 各階段耗時。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

_COLS = ("#", "line_id", "axis", "x1", "y1", "x2", "y2", "length_px")


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)

        top = QHBoxLayout()
        self.lbl_verdict = QLabel("—")
        self.lbl_verdict.setStyleSheet("font-size: 16pt; font-weight: bold;")
        self.lbl_info = QLabel("")
        top.addWidget(self.lbl_verdict)
        top.addSpacing(16)
        top.addWidget(self.lbl_info, 1)
        lay.addLayout(top)

        self.table = QTableWidget(0, len(_COLS))
        self.table.setHorizontalHeaderLabels(_COLS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, 1)

    def show_result(self, r):
        """r: session.SessionResult"""
        self.table.setRowCount(0)
        if not r.ok:
            self.lbl_verdict.setText("錯誤")
            self.lbl_verdict.setStyleSheet(
                "font-size:16pt;font-weight:bold;color:#c02020;")
            self.lbl_info.setText(r.message)
            return

        color = {"OK": "#0a8a0a", "NG": "#c02020", "Placement": "#b08000",
                 "PLACEMENT": "#b08000", "Taught": "#1060c0"}.get(
                     r.verdict, "#404040")
        self.lbl_verdict.setText(r.verdict)
        self.lbl_verdict.setStyleSheet(
            "font-size:16pt;font-weight:bold;color:%s;" % color)

        fams = "  ".join("%s: %d 條 pitch=%.1f (%s)"
                         % (f.axis, f.line_count, f.pitch_px, f.mode)
                         for f in r.families)
        ms = "  ".join("%s=%.0fms" % (k, v) for k, v in r.stage_ms.items())
        self.lbl_info.setText("angle=%.2f°   %s   |   %s   總計 %.0fms"
                              % (r.angle_deg, fams, ms, r.total_ms))

        for i, d in enumerate(r.defects, 1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            vals = (str(i), str(d.line_id), d.axis,
                    "%.1f" % d.x1, "%.1f" % d.y1,
                    "%.1f" % d.x2, "%.1f" % d.y2, "%.1f" % d.length_px)
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, c, item)
        self.table.resizeColumnsToContents()
