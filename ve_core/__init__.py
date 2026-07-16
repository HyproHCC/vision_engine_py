# -*- coding: utf-8 -*-
"""ve_core —— 陶瓷片切割線斷線檢測純演算法函式庫。

無 I/O、無 UI 相依、無網路相依。輸入 np.ndarray、輸出 dataclass。
呼叫端（ve_server / ve_ui）一律從本模組頂層 import；
子模組視為內部實作，介面不保證穩定。

    from ve_core import inspect, teach, AlgoConfig, RoiSpec, ...
"""
from .crossval import cross_validate
from .errors import (FrameNotFound, LinesNotFound, TaughtParamsError,
                     VeCoreError)
from .judge import JudgeCriteria, reference_judge
from .pipeline import (FamilyGeometry, build_family_geometry,
                       detect_family_breaks, estimate_angles,
                       find_family_lines, inspect, map_line_to_original,
                       placement_angle, resolve_roi, teach)
from .types import (FAMILY_AXES, TP_VERSION, AlgoConfig, BreakDefect,
                    DetectionAnomaly, FamilyDetection, FamilyParams,
                    InspectResult, PlacementResult, Rect, RoiSpec,
                    TaughtParams, TeachResult, Thresholds, Verdict)

__all__ = [
    # errors
    "VeCoreError", "FrameNotFound", "LinesNotFound", "TaughtParamsError",
    # types
    "FAMILY_AXES", "TP_VERSION", "AlgoConfig", "BreakDefect",
    "DetectionAnomaly", "FamilyDetection", "FamilyParams", "InspectResult",
    "PlacementResult", "Rect", "RoiSpec", "TaughtParams", "TeachResult",
    "Thresholds", "Verdict",
    # pipeline (full runs)
    "inspect", "teach",
    # pipeline (staged API for tuning UI)
    "resolve_roi", "estimate_angles", "placement_angle",
    "FamilyGeometry", "build_family_geometry", "find_family_lines",
    "detect_family_breaks", "map_line_to_original",
    # cross-validation (frame-edge pairing; inspect() only, reference/debug)
    "cross_validate",
    # judge (reference only; production judge lives in LabVIEW)
    "JudgeCriteria", "reference_judge",
]

__version__ = "1.0.0"
