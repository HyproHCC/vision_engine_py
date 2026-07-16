# -*- coding: utf-8 -*-
"""調機工具進入點：python -m ve_ui.app [影像路徑]"""
import sys

from PySide6.QtWidgets import QApplication

from .loader import load_gray
from .main_window import MainWindow


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    win = MainWindow()
    win.show()
    # 可選：命令列直接帶影像
    if len(argv) > 1:
        try:
            gray = load_gray(argv[1])
            win.session.set_image(gray, argv[1])
            win.view.set_image(gray)
            win.recompute()
        except IOError as e:
            print(e, file=sys.stderr)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
