# -*- coding: utf-8 -*-
"""參考 Judge —— 僅供 MVP／調機工具本地顯示 OK/NG。

**生產最終判定以 LabVIEW 端 Judge 為準**（模組職責分工已定案）。
本檔欄位名刻意對齊 Recipe.ctl：judge_max_break_px / judge_max_breaks，
使調機工具上調出的準則可直接抄進配方。

準則語意（與 LabVIEW 端約定一致）：
- 單一斷點長度 <= judge_max_break_px 視為可容忍小斷點
- 可容忍以外（超長）斷點數量為 0，且全部斷點總數 <= judge_max_breaks
  時判 OK，否則 NG
- judge_max_break_px <= 0 表示「任何斷點皆 NG」（預設嚴格）
"""
from dataclasses import dataclass

from .types import InspectResult, PlacementResult, Verdict


@dataclass
class JudgeCriteria:
    judge_max_break_px: float = 0.0   # 可容忍的單一斷點最大長度；<=0 = 零容忍
    judge_max_breaks: int = 0         # 可容忍的斷點總數上限


def reference_judge(result, criteria: JudgeCriteria) -> Verdict:
    """engine 結果 + 配方準則 → 最終 verdict（參考實作）。"""
    if isinstance(result, PlacementResult):
        return Verdict.PLACEMENT
    assert isinstance(result, InspectResult)
    if not result.defects:
        return Verdict.OK
    if criteria.judge_max_break_px <= 0:
        return Verdict.NG
    oversize = [d for d in result.defects
                if d.length_px > criteria.judge_max_break_px]
    if oversize:
        return Verdict.NG
    if len(result.defects) > criteria.judge_max_breaks:
        return Verdict.NG
    return Verdict.OK
