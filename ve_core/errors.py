# -*- coding: utf-8 -*-
"""ve_core 例外階層。

ve_core 不知道協定 error code；ve_server/engine.py 負責把這些例外
映射到 PROTOCOL.md 第 9 節的 engine error_code：

    FrameNotFound     -> 102
    LinesNotFound     -> 103
    TaughtParamsError -> 104
    其它 VeCoreError / Exception -> 110
"""


class VeCoreError(Exception):
    """ve_core 所有可預期失敗的基底。"""


class FrameNotFound(VeCoreError):
    """AutoFrame 找不到大黑框內緣，或 ROI 退化。"""


class LinesNotFound(VeCoreError):
    """找不到切割線（發現式失敗 / 驗證式定位失敗 / pitch 估計失敗）。"""


class TaughtParamsError(VeCoreError):
    """taught_params 缺漏、版本不符或結構錯誤。"""
