# -*- coding: utf-8 -*-
"""InspectionSession —— 分段快取的調機執行核心（無 Qt 相依，可獨立測試）。

管線階段與相依（成本為 3840x2748 量級）：

    S_ROI     resolve_roi              便宜   ROI 參數變動
    S_ANGLE   estimate_angles          貴     角度搜尋參數變動
    S_GEOM    build_family_geometry x2 貴     角度/ROI 下游
    S_LINES   find_family_lines        中     找線參數或 taught 變動
    S_BREAKS  detect_family_breaks     毫秒   門檻滑桿變動

參數變動只把 dirty level 往上推到對應階段；run() 從 dirty 階段
往下重算並更新快取。**動斷線門檻滑桿只重算 S_BREAKS**，
「即時重跑重繪」因此真的即時。

模式：
    discovery      發現式檢測（無 taught）
    taught         驗證式檢測（用 session.taught）
    teach          教導：發現式 + 產出 TaughtParams 供目視確認
"""
import time
from dataclasses import dataclass, field

import numpy as np

import ve_core

# dirty levels（數字小 = 越上游）
S_CLEAN = 99
S_BREAKS = 4
S_LINES = 3
S_GEOM = 2
S_ANGLE = 1
S_ROI = 0


@dataclass
class FamilyView:
    """單族顯示資料：線段與斷點都已在**原圖座標**。"""
    axis: str
    angle_deg: float
    pitch_px: float
    line_count: int
    segments: list          # [((x1,y1),(x2,y2)), ...] 每條線
    mode: str


@dataclass
class SessionResult:
    ok: bool                # False = 演算法錯誤（訊息在 message）
    message: str = ""
    placement: bool = False
    engine_status: str = ""          # OK/NG/PLACEMENT_ERROR（引擎原始結論）
    verdict: str = ""                # 參考 Judge 後的最終判定（MVP 顯示用）
    angle_deg: float = 0.0
    roi_rect: object = None          # ve_core.Rect（原圖座標）
    families: list = field(default_factory=list)   # [FamilyView]
    defects: list = field(default_factory=list)    # [BreakDefect] 原圖座標
    taught: object = None            # teach 模式時的 TaughtParams
    stage_ms: dict = field(default_factory=dict)   # 各階段耗時
    total_ms: float = 0.0


class InspectionSession:
    def __init__(self):
        self.cfg = ve_core.AlgoConfig()
        self.thresholds = ve_core.Thresholds.from_config(self.cfg)
        self.judge = ve_core.JudgeCriteria()
        self.roi = ve_core.RoiSpec("AutoFrame")
        self.angle_tol_deg = 5.0
        self.mode = "discovery"          # discovery | taught | teach
        self.taught = None               # ve_core.TaughtParams
        self.gray = None
        self.image_path = ""
        self._dirty = S_ROI
        # caches
        self._roi_rect = None
        self._angles = None
        self._geoms = {}                 # axis -> FamilyGeometry
        self._line_res = {}              # axis -> dict|None

    # ------------------------------------------------ inputs
    def set_image(self, gray: np.ndarray, path: str = ""):
        self.gray = gray
        self.image_path = path
        self._dirty = S_ROI

    def set_mode(self, mode: str):
        assert mode in ("discovery", "taught", "teach")
        if mode != self.mode:
            self.mode = mode
            self._invalidate(S_LINES)    # 找線來源改變

    def set_taught(self, taught):
        self.taught = taught
        if self.mode == "taught":
            self._invalidate(S_LINES)

    def set_roi(self, roi: "ve_core.RoiSpec"):
        self.roi = roi
        self._invalidate(S_ROI)

    def set_angle_tol(self, tol: float):
        self.angle_tol_deg = float(tol)
        # 只影響放置判定（在 run 內即時比較），角度快取仍有效
        self._invalidate(S_GEOM)

    def update_params(self, group: str, **kw):
        """group: 'roi' | 'angle' | 'lines' | 'thresholds'"""
        if group == "thresholds":
            for k, v in kw.items():
                setattr(self.thresholds, k, v)
            self._invalidate(S_BREAKS)
            return
        for k, v in kw.items():
            setattr(self.cfg, k, v)
        if group == "roi":
            self._invalidate(S_ROI)
        elif group == "angle":
            self._invalidate(S_ANGLE)
        elif group == "lines":
            self._invalidate(S_LINES)
        else:
            raise ValueError(group)

    def update_judge(self, **kw):
        for k, v in kw.items():
            setattr(self.judge, k, v)
        # judge 不動快取，run 尾端重新判定即可
        self._invalidate(S_BREAKS)

    def _invalidate(self, level: int):
        self._dirty = min(self._dirty, level)

    # ------------------------------------------------ run
    def run(self) -> SessionResult:
        if self.gray is None:
            return SessionResult(ok=False, message="尚未載入影像")
        t_total = time.perf_counter()
        stage_ms = {}
        try:
            # S_ROI
            if self._dirty <= S_ROI or self._roi_rect is None:
                t0 = time.perf_counter()
                self._roi_rect = ve_core.resolve_roi(self.gray, self.roi,
                                                     self.cfg)
                stage_ms["roi"] = (time.perf_counter() - t0) * 1000
                self._dirty = min(self._dirty, S_ANGLE)
                self._angles = None

            # S_ANGLE
            if self._dirty <= S_ANGLE or self._angles is None:
                t0 = time.perf_counter()
                self._angles = ve_core.estimate_angles(self.gray,
                                                       self._roi_rect,
                                                       self.cfg)
                stage_ms["angle"] = (time.perf_counter() - t0) * 1000
                self._geoms = {}

            angle_deg = ve_core.placement_angle(self._angles)
            if abs(angle_deg) > self.angle_tol_deg:
                self._dirty = S_GEOM     # 下次 tol 放寬時從 GEOM 續跑
                return SessionResult(
                    ok=True, placement=True,
                    engine_status="PLACEMENT_ERROR", verdict="Placement",
                    angle_deg=round(angle_deg, 3),
                    roi_rect=self._roi_rect,
                    stage_ms=stage_ms,
                    total_ms=(time.perf_counter() - t_total) * 1000)

            # S_GEOM
            if self._dirty <= S_GEOM or not self._geoms:
                t0 = time.perf_counter()
                self._geoms = {
                    ax: ve_core.build_family_geometry(
                        self.gray, ax, self._angles[ax], self.roi,
                        self._roi_rect, self.cfg)
                    for ax in ve_core.FAMILY_AXES}
                stage_ms["geom"] = (time.perf_counter() - t0) * 1000
                self._line_res = {}

            # S_LINES
            if self._dirty <= S_LINES or not self._line_res:
                t0 = time.perf_counter()
                taught = self.taught if self.mode == "taught" else None
                self._line_res = {
                    ax: ve_core.find_family_lines(self._geoms[ax], self.cfg,
                                                  taught)
                    for ax in ve_core.FAMILY_AXES}
                stage_ms["lines"] = (time.perf_counter() - t0) * 1000

            # S_BREAKS（教導模式不跑斷點）
            t0 = time.perf_counter()
            defects = []
            families = []
            lines_total = 0
            eff_thresholds = self.thresholds
            if self.mode == "taught" and self.taught is not None:
                eff_thresholds = ve_core.Thresholds.from_config(
                    self.cfg).merged_with(
                        self.taught.thresholds.to_json_dict())
            for ax in ve_core.FAMILY_AXES:
                res = self._line_res.get(ax)
                geom = self._geoms.get(ax)
                if res is None or geom is None:
                    continue
                if self.mode != "teach":
                    defects.extend(ve_core.detect_family_breaks(
                        geom, res["positions"], eff_thresholds, lines_total))
                lines_total += len(res["positions"])
                families.append(FamilyView(
                    axis=ax,
                    angle_deg=round(geom.angle_deg, 3),
                    pitch_px=round(res["pitch_px"], 2),
                    line_count=len(res["positions"]),
                    segments=[ve_core.map_line_to_original(geom, p)
                              for p in res["positions"]],
                    mode=res["mode"]))
            stage_ms["breaks"] = (time.perf_counter() - t0) * 1000
            self._dirty = S_CLEAN

            if lines_total == 0:
                return SessionResult(
                    ok=False, message="兩族皆找不到切割線 (LinesNotFound)",
                    angle_deg=round(angle_deg, 3), roi_rect=self._roi_rect,
                    stage_ms=stage_ms,
                    total_ms=(time.perf_counter() - t_total) * 1000)

            taught_out = None
            if self.mode == "teach":
                fams = []
                for ax in ve_core.FAMILY_AXES:
                    res = self._line_res.get(ax)
                    geom = self._geoms.get(ax)
                    if res is None:
                        continue
                    fams.append(ve_core.FamilyParams(
                        axis=ax,
                        angle_deg=round(geom.angle_deg, 3),
                        pitch_px=round(res["pitch_px"], 2),
                        line_count=len(res["positions"]),
                        positions_px=[round(p, 1) for p in res["positions"]]))
                import datetime, os
                taught_out = ve_core.TaughtParams(
                    families=fams,
                    thresholds=self.thresholds,
                    reference={"taught_at": datetime.datetime.now()
                               .isoformat(timespec="seconds"),
                               "image": os.path.basename(self.image_path)})

            engine_status = "OK" if (self.mode == "teach" or not defects) \
                else "NG"
            # 參考 Judge（生產以 LabVIEW Judge 為準）
            if self.mode == "teach":
                verdict = "Taught"
            else:
                ir = ve_core.InspectResult(
                    verdict=ve_core.Verdict.NG if defects else ve_core.Verdict.OK,
                    angle_deg=round(angle_deg, 3), lines_found=lines_total,
                    defects=defects, roi_used=self._roi_rect,
                    detection_mode=self.mode)
                verdict = ve_core.reference_judge(ir, self.judge).name

            return SessionResult(
                ok=True, engine_status=engine_status, verdict=verdict,
                angle_deg=round(angle_deg, 3), roi_rect=self._roi_rect,
                families=families, defects=defects, taught=taught_out,
                stage_ms=stage_ms,
                total_ms=(time.perf_counter() - t_total) * 1000)

        except ve_core.FrameNotFound as e:
            return SessionResult(ok=False, message="找框失敗：%s" % e,
                                 stage_ms=stage_ms)
        except ve_core.LinesNotFound as e:
            return SessionResult(ok=False, message="找線失敗：%s" % e,
                                 stage_ms=stage_ms)
        except ve_core.VeCoreError as e:
            return SessionResult(ok=False, message="演算法錯誤：%s" % e,
                                 stage_ms=stage_ms)
