# -*- coding: utf-8 -*-
"""ve_core 資料合約。

所有公開輸入/輸出型別集中此檔。JSON 序列化格式與 PROTOCOL.md
一一對應且**凍結**（退出條件 7：taught_params JSON 即生產格式，
LabVIEW 原樣搬運不解析）；schema 演進只動 TP_VERSION。

座標紀律：BreakDefect 一律原圖座標。TaughtParams.positions_px
定義為「該線族去旋轉座標系中、以分析區原點為基準」的線位置
（此定義自 v1 起凍結，寫入 tp_version=1）。

純字串 <-> dataclass 轉換不算 I/O，故放在 ve_core。
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .errors import TaughtParamsError

TP_VERSION = 1
FAMILY_AXES = ("v", "h")


# ---------------------------------------------------------------- geometry
@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    def to_json_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

    @classmethod
    def from_json_dict(cls, d: dict) -> "Rect":
        return cls(int(d["x"]), int(d["y"]), int(d["w"]), int(d["h"]))


@dataclass(frozen=True)
class RoiSpec:
    """ROI 指定方式。mode='AutoFrame' 時 rect 忽略。

    'AutoInRoi'：rect 為操作員粗略框出的大黑框範圍（原圖座標），
    在此範圍內精確定位內緣，取代對全圖跑 find_inner_roi。
    """
    mode: str = "AutoFrame"          # "AutoFrame" | "Manual" | "AutoInRoi"
    rect: Optional[Rect] = None

    def __post_init__(self):
        if self.mode not in ("AutoFrame", "Manual", "AutoInRoi"):
            raise ValueError("RoiSpec.mode must be AutoFrame|Manual|AutoInRoi")
        if self.mode in ("Manual", "AutoInRoi") and self.rect is None:
            raise ValueError("RoiSpec: %s mode requires rect" % self.mode)


# ---------------------------------------------------------------- config
@dataclass
class AlgoConfig:
    """演算法預設參數（無 taught_params 時的發現式檢測用）。

    欄位與 ve_server config.json 的 algo 區塊一一對應。
    """
    frame_dark_max: int = 60
    ceramic_min: int = 90
    angle_search_deg: float = 6.0
    angle_coarse_step: float = 0.5
    angle_fine_step: float = 0.05
    peak_min_dist_ratio: float = 0.6
    ridge_kernel_px: int = 15
    cut_bright_thresh: float = 180
    min_break_len_px: int = 8
    band_halfwidth_px: int = 4
    gap_merge_px: int = 6
    edge_guard_px: int = 10
    angle_est_max_side: int = 1400
    # 框邊配對法交叉驗證（crossval.py）；待對照影像校準的暫定值
    xval_inset_px: int = 40
    xval_edge_band_px: int = 4
    xval_angle_dispersion_tol_deg: float = 1.5
    xval_perp_tol_deg: float = 3.0
    # 找線方法：projection（投影法，亮線，50k 片型）｜
    # edge_pairing（框邊配對法，暗線，Ctype 片型）。極性隨方法走，
    # 不再有獨立的極性開關（兩者互斥，各自的線族極性假設已固定）。
    line_find_method: str = "projection"

    @classmethod
    def from_dict(cls, d: dict) -> "AlgoConfig":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class Thresholds:
    """剖面判定門檻。對照影像量化後只改參數不改碼。"""
    cut_bright_thresh: float = 180
    min_break_len_px: int = 8
    band_halfwidth_px: int = 4
    gap_merge_px: int = 6
    edge_guard_px: int = 10

    @classmethod
    def from_config(cls, cfg: AlgoConfig) -> "Thresholds":
        return cls(cut_bright_thresh=cfg.cut_bright_thresh,
                   min_break_len_px=cfg.min_break_len_px,
                   band_halfwidth_px=cfg.band_halfwidth_px,
                   gap_merge_px=cfg.gap_merge_px,
                   edge_guard_px=cfg.edge_guard_px)

    def merged_with(self, override: Optional[dict]) -> "Thresholds":
        """taught_params.thresholds 覆蓋預設（沿用舊 pipeline 語意：
        taught 內出現的鍵覆蓋，未出現的鍵用預設）。"""
        if not override:
            return self
        d = dataclasses.asdict(self)
        d.update({k: v for k, v in override.items() if k in d})
        return Thresholds(**d)

    def to_json_dict(self) -> dict:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------- taught
@dataclass
class FamilyParams:
    axis: str                       # "v" | "h"
    angle_deg: float
    pitch_px: float
    line_count: int
    positions_px: list = field(default_factory=list)

    def to_json_dict(self) -> dict:
        return {"axis": self.axis,
                "angle_deg": self.angle_deg,
                "pitch_px": self.pitch_px,
                "line_count": self.line_count,
                "positions_px": list(self.positions_px)}


@dataclass
class TaughtParams:
    """教導結果。JSON 格式 = PROTOCOL.md 第 7 節 = 生產凍結格式。"""
    families: list                  # list[FamilyParams]
    thresholds: Thresholds
    reference: dict = field(default_factory=dict)
    tp_version: int = TP_VERSION

    def family(self, axis: str) -> Optional[FamilyParams]:
        return next((f for f in self.families if f.axis == axis), None)

    def to_json_dict(self) -> dict:
        return {"tp_version": self.tp_version,
                "families": [f.to_json_dict() for f in self.families],
                "thresholds": self.thresholds.to_json_dict(),
                "reference": dict(self.reference)}

    def to_json(self) -> str:
        return json.dumps(self.to_json_dict(), ensure_ascii=True,
                          separators=(",", ":"))

    @classmethod
    def from_json_dict(cls, d: object) -> "TaughtParams":
        """驗證 + 解析。失敗丟 TaughtParamsError（沿用舊 pipeline 的
        驗證條件：必須是 dict、tp_version 相符、families 為 list）。"""
        if (not isinstance(d, dict)
                or d.get("tp_version") != TP_VERSION
                or not isinstance(d.get("families"), list)):
            raise TaughtParamsError(
                "taught_params missing or version mismatch")
        fams = []
        for f in d["families"]:
            if not isinstance(f, dict) or "axis" not in f:
                raise TaughtParamsError("taught_params family malformed")
            fams.append(FamilyParams(
                axis=str(f["axis"]),
                angle_deg=float(f.get("angle_deg", 0.0)),
                pitch_px=float(f.get("pitch_px", 0.0)),
                line_count=int(f.get("line_count", len(f.get("positions_px", [])))),
                positions_px=[float(p) for p in f.get("positions_px", [])]))
        th = Thresholds().merged_with(
            d.get("thresholds") if isinstance(d.get("thresholds"), dict) else None)
        return cls(families=fams, thresholds=th,
                   reference=dict(d.get("reference", {})),
                   tp_version=int(d["tp_version"]))

    @classmethod
    def from_json(cls, s: str) -> "TaughtParams":
        try:
            d = json.loads(s)
        except Exception as e:
            raise TaughtParamsError("taught_params invalid JSON: %s" % e)
        return cls.from_json_dict(d)


# ---------------------------------------------------------------- results
class Verdict(Enum):
    """ve_core 的原始結論（engine status），非最終系統判定。

    生產上最終 verdict 由 LabVIEW Judge 依配方準則產生；
    MVP/調機工具用 reference_judge()（見 judge.py）本地顯示。
    """
    OK = "OK"
    NG = "NG"
    PLACEMENT = "PLACEMENT_ERROR"


@dataclass
class BreakDefect:
    line_id: int
    x1: float                       # 原圖座標
    y1: float
    x2: float
    y2: float
    length_px: float
    axis: str = ""                  # 內部/UI 輔助欄位，不進協定 JSON

    def to_json_dict(self) -> dict:
        """PROTOCOL.md defects 元素格式（不含 axis）。"""
        return {"line_id": self.line_id,
                "x1": self.x1, "y1": self.y1,
                "x2": self.x2, "y2": self.y2,
                "length_px": self.length_px}


@dataclass
class FamilyDetection:
    """單一線族的偵測明細（UI overlay 與除錯用；協定只取彙總）。"""
    axis: str
    angle_deg: float
    pitch_px: float
    positions_px: list              # 分析區座標
    region: Rect                    # 旋轉座標系中的分析區
    mode: str                       # "discovery" | "taught"
    break_lengths_px: list = field(default_factory=list)
    # 與 positions_px 等長、依序：該線總斷線長度(px)，無斷線為 0.0。
    # 只有 inspect() 會填；teach() 不跑斷線偵測，維持預設空陣列。


@dataclass
class InspectResult:
    verdict: Verdict
    angle_deg: float
    lines_found: int
    defects: list                   # list[BreakDefect]，原圖座標
    roi_used: Rect                  # 原圖座標（估角用 ROI）
    detection_mode: str             # "taught" | "discovery" | "n/a"
    families: list = field(default_factory=list)   # list[FamilyDetection]

    def defects_json(self) -> list:
        return [d.to_json_dict() for d in self.defects]

    def break_lengths_json(self) -> dict:
        """{"v": [...], "h": [...]}，每族依 positions_px 線序的總斷線長度。"""
        out = {"v": [], "h": []}
        for f in self.families:
            if f.axis in out:
                out[f.axis] = [round(float(x), 1) for x in f.break_lengths_px]
        return out


@dataclass
class DetectionAnomaly:
    """框邊配對法交叉驗證失敗（需求 4）。與斷線 NG 明確區分：
    偵測結果本身不可信，不是「有偵測到斷線」。只在 inspect() 出現，
    teach() 不跑交叉驗證。"""
    roi_used: Rect
    angle_deg: float
    reasons: list                   # list[str]，可能同時多個原因碼
    detail: dict = field(default_factory=dict)   # 除錯用數值明細


@dataclass
class TeachResult:
    angle_deg: float
    roi_used: Rect
    taught: TaughtParams
    families: list = field(default_factory=list)   # list[FamilyDetection]

    def preview_json(self) -> dict:
        return {"families": [
            {"axis": f.axis, "angle_deg": f.angle_deg,
             "line_count": f.line_count, "pitch_px": f.pitch_px}
            for f in self.taught.families]}


@dataclass
class PlacementResult:
    """放置異常（教導/檢測共用）。"""
    angle_deg: float
    roi_used: Rect
