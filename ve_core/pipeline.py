# -*- coding: utf-8 -*-
"""檢測管線：估角(兩族) → 放置檢查 → 整張圖去旋轉
→ 旋轉座標系內重新定位分析區 → 找線 → 剖面斷點 → 座標轉回原圖。

設計重點（沿用已驗證行為）：每個線族「旋轉整張影像」後在旋轉座標系中
**重新定位**內緣 ROI（AutoFrame 重跑 find_inner_roi；Manual 取旋轉後
內接矩形）。這消除了軸對齊 ROI 在旋轉影像上包進框角/邊緣過渡帶造成的假線。

本模組不做 I/O：輸入 np.ndarray、輸出 dataclass。載圖、NG 留存、
協定組裝都在 ve_server / ve_ui。

分段 API（供 ve_ui 分段快取；成本標註為 3840x2748 實測量級）：

    resolve_roi()          便宜      ROI 參數變動時重跑
    estimate_angles()      貴(秒級)  角度搜尋參數變動時重跑
    build_family_geometry()貴        角度或 ROI 變動時重跑（每族一次）
    find_family_lines()    中        找線參數 / taught 變動時重跑
    detect_family_breaks() 便宜(毫秒) 門檻滑桿即時重跑只需此段

inspect() / teach() 為上述階段的組合，ve_server 與批次跑分直接用。
taught positions_px 定義：該族旋轉座標系中、以分析區原點為基準的線位置。
"""
import datetime
import logging
from dataclasses import dataclass, field

import numpy as np

from . import breaks as breaks_mod
from . import crossval as crossval_mod
from . import derotate as rot_mod
from . import edge_lines as edge_lines_mod
from . import frame as frame_mod
from . import lines as lines_mod
from .errors import FrameNotFound, LinesNotFound
from .types import (FAMILY_AXES, AlgoConfig, BreakDefect, DetectionAnomaly,
                    FamilyDetection, FamilyParams, InspectResult,
                    PlacementResult, Rect,
                    RoiSpec, TaughtParams, TeachResult, Thresholds, Verdict)

logger = logging.getLogger("ve_core")


def _find_inner_roi_in_rect(image: np.ndarray, x, y, w, h,
                            cfg: AlgoConfig, margin: int = 4) -> Rect:
    """在給定粗略矩形（AutoInRoi 的操作員框選）內裁子圖找大黑框內緣，
    結果平移回 image 的座標系（不一定是原圖，也可能是旋轉座標系）。"""
    x = max(0, int(x)); y = max(0, int(y))
    w = min(int(w), image.shape[1] - x)
    h = min(int(h), image.shape[0] - y)
    if w < 100 or h < 100:
        raise FrameNotFound("AutoInRoi: rough roi degenerate")
    sub = image[y:y + h, x:x + w]
    fx, fy, fw, fh = frame_mod.find_inner_roi(sub, ceramic_min=cfg.ceramic_min,
                                              margin=margin)
    return Rect(fx + x, fy + y, fw, fh)


# ================================================================ stages
def resolve_roi(gray: np.ndarray, roi: RoiSpec, cfg: AlgoConfig) -> Rect:
    """原圖座標的 ROI（估角用；分析區之後在旋轉座標系重新定位）。"""
    if roi.mode == "Manual":
        r = roi.rect
        x, y = int(r.x), int(r.y)
        w, h = int(r.w), int(r.h)
        x = max(0, x); y = max(0, y)
        w = min(w, gray.shape[1] - x); h = min(h, gray.shape[0] - y)
        if w < 100 or h < 100:
            raise FrameNotFound("manual ROI degenerate")
        rect = Rect(x, y, w, h)
    elif roi.mode == "AutoInRoi":
        r = roi.rect
        rect = _find_inner_roi_in_rect(gray, r.x, r.y, r.w, r.h, cfg)
    else:
        x, y, w, h = frame_mod.find_inner_roi(gray, ceramic_min=cfg.ceramic_min)
        rect = Rect(x, y, w, h)
    logger.debug("resolve_roi mode=%s -> %r", roi.mode, rect)
    return rect


def estimate_angles(gray: np.ndarray, roi_rect: Rect, cfg: AlgoConfig) -> dict:
    """兩族方向角 {'v': deg, 'h': deg}。"""
    sub = gray[roi_rect.y:roi_rect.y + roi_rect.h,
               roi_rect.x:roi_rect.x + roi_rect.w]
    kw = dict(search_deg=cfg.angle_search_deg,
              coarse_step=cfg.angle_coarse_step,
              fine_step=cfg.angle_fine_step,
              max_side=cfg.angle_est_max_side)
    angles = {ax: rot_mod.estimate_angle(sub, ax, **kw) for ax in FAMILY_AXES}
    logger.debug("estimate_angles -> %r", angles)
    return angles


def placement_angle(angles: dict) -> float:
    """放置角以兩族中絕對值較大者代表。"""
    return max(angles.values(), key=abs)


@dataclass
class FamilyGeometry:
    """單一線族的去旋轉幾何：旋轉影像、仿射矩陣、分析區。"""
    axis: str
    angle_deg: float
    rot: np.ndarray = field(repr=False)
    M: np.ndarray = field(repr=False)
    Minv: np.ndarray = field(repr=False)
    region: Rect

    @property
    def sub(self) -> np.ndarray:
        r = self.region
        return self.rot[r.y:r.y + r.h, r.x:r.x + r.w]


def build_family_geometry(gray: np.ndarray, axis: str, angle_deg: float,
                          roi: RoiSpec, roi_rect: Rect,
                          cfg: AlgoConfig) -> FamilyGeometry:
    """整張圖去旋轉 + 旋轉座標系內重新定位分析區。"""
    rot, M, Minv = rot_mod.rotate_keep_center(gray, angle_deg)
    if roi.mode == "Manual":
        x, y, w, h = rot_mod.map_rect_forward(
            (roi_rect.x, roi_rect.y, roi_rect.w, roi_rect.h), M)
        x = max(0, x); y = max(0, y)
        w = min(w, rot.shape[1] - x); h = min(h, rot.shape[0] - y)
        if w < 100 or h < 100:
            raise FrameNotFound("manual ROI degenerate after rotation")
        region = Rect(x, y, w, h)
    elif roi.mode == "AutoInRoi":
        # 操作員粗略框（原圖座標）隨影像一起轉到旋轉座標系，
        # 在該範圍內重新精確定位內緣——粗框本身不直接當分析區。
        rx, ry, rw, rh = rot_mod.map_rect_forward(
            (roi.rect.x, roi.rect.y, roi.rect.w, roi.rect.h), M)
        try:
            region = _find_inner_roi_in_rect(rot, rx, ry, rw, rh, cfg,
                                             margin=6)
        except FrameNotFound as e:
            raise FrameNotFound("post-rotation: %s" % e)
    else:
        try:
            x, y, w, h = frame_mod.find_inner_roi(
                rot, ceramic_min=cfg.ceramic_min, margin=6)
        except FrameNotFound as e:
            raise FrameNotFound("post-rotation: %s" % e)
        region = Rect(x, y, w, h)
    return FamilyGeometry(axis=axis, angle_deg=angle_deg,
                          rot=rot, M=M, Minv=Minv, region=region)


def _dark_line_view(sub: np.ndarray) -> np.ndarray:
    """切割線在實機影像上是暗線；反相成亮線後交給既有「亮線」演算法
    （ridge_bandpass / band_profile / find_dark_runs 皆不改）。
    唯一反相入口，同時對 discovery / taught / inspect / teach 生效
    （ARCHITECTURE.md 3.2）。"""
    return 255 - sub


def find_family_lines(geom: FamilyGeometry, cfg: AlgoConfig,
                      taught: TaughtParams = None):
    """找線。回傳 {'positions': [...], 'pitch_px': f, 'mode': str}；
    該族無線（taught 中無此 axis / 發現式找不到）回 None。
    taught 模式定位失敗丟 LinesNotFound（驗證式的失敗是硬錯誤）。"""
    sub = _dark_line_view(geom.sub)
    if taught is not None:
        fam = taught.family(geom.axis)
        if fam is None:
            return None  # 該片型此方向無線（允許單方向片型）
        res = lines_mod.verify_lines(sub, geom.axis,
                                     fam.positions_px, fam.pitch_px,
                                     ridge_kernel_px=cfg.ridge_kernel_px)
        res["mode"] = "taught"
        logger.debug("find_family_lines axis=%s taught: n=%d pitch=%.2f",
                    geom.axis, len(res["positions"]), res["pitch_px"])
        return res
    try:
        res = lines_mod.discover_lines(sub, geom.axis,
                                       cfg.peak_min_dist_ratio,
                                       ridge_kernel_px=cfg.ridge_kernel_px)
    except LinesNotFound as e:
        logger.info("no lines on axis=%s (%s)", geom.axis, e)
        return None
    res["mode"] = "discovery"
    logger.debug("find_family_lines axis=%s discovery: n=%d pitch=%.2f",
                geom.axis, len(res["positions"]), res["pitch_px"])
    return res


def detect_family_breaks(geom: FamilyGeometry, positions: list,
                         thresholds: Thresholds,
                         line_id_start: int) -> list:
    """單族斷點偵測，回傳 list[BreakDefect]（原圖座標）。
    line_id 自 line_id_start+1 起連續編號（跨族累計由呼叫端負責）。"""
    sub = _dark_line_view(geom.sub)
    ax0, ay0 = geom.region.x, geom.region.y
    defects = []
    lid = line_id_start
    for pos in positions:
        lid += 1
        for d in breaks_mod.detect_breaks_on_line(sub, geom.axis,
                                                  lid, pos, thresholds):
            # 分析區座標 → 旋轉座標 → 原圖座標
            p1 = (d["_p1_rot"][0] + ax0, d["_p1_rot"][1] + ay0)
            p2 = (d["_p2_rot"][0] + ax0, d["_p2_rot"][1] + ay0)
            pts = rot_mod.map_points_back(np.array([p1, p2]), geom.Minv)
            defects.append(BreakDefect(
                line_id=d["line_id"],
                x1=round(float(pts[0, 0]), 1),
                y1=round(float(pts[0, 1]), 1),
                x2=round(float(pts[1, 0]), 1),
                y2=round(float(pts[1, 1]), 1),
                length_px=round(d["length_px"], 1),
                axis=geom.axis))
    return defects


def map_line_to_original(geom: FamilyGeometry, pos: float) -> tuple:
    """把分析區內位置 pos 的整條線映回原圖座標，供 overlay 繪製。
    回傳 ((x1, y1), (x2, y2))。"""
    r = geom.region
    if geom.axis == "v":
        p1 = (pos + r.x, 0.0 + r.y)
        p2 = (pos + r.x, float(r.h - 1) + r.y)
    else:
        p1 = (0.0 + r.x, pos + r.y)
        p2 = (float(r.w - 1) + r.x, pos + r.y)
    pts = rot_mod.map_points_back(np.array([p1, p2]), geom.Minv)
    return ((float(pts[0, 0]), float(pts[0, 1])),
            (float(pts[1, 0]), float(pts[1, 1])))


def _family_params_from(geom: FamilyGeometry, res: dict) -> FamilyParams:
    """taught_params 的族項（沿用舊 pipeline 的欄位取整）。"""
    return FamilyParams(
        axis=geom.axis,
        angle_deg=round(geom.angle_deg, 3),
        pitch_px=round(res["pitch_px"], 2),
        line_count=len(res["positions"]),
        positions_px=[round(p, 1) for p in res["positions"]])


def _family_detection_from(geom: FamilyGeometry, res: dict,
                           break_lengths: list = None) -> FamilyDetection:
    return FamilyDetection(
        axis=geom.axis,
        angle_deg=round(geom.angle_deg, 3),
        pitch_px=round(res["pitch_px"], 2),
        positions_px=list(res["positions"]),
        region=geom.region,
        mode=res["mode"],
        break_lengths_px=break_lengths if break_lengths is not None else [])


# ================================================================ compose
def inspect(gray: np.ndarray, cfg: AlgoConfig, roi: RoiSpec,
            angle_tol_deg: float = 5.0,
            taught: TaughtParams = None):
    """完整檢測。回傳 InspectResult / PlacementResult / DetectionAnomaly。

    可能丟出：FrameNotFound、LinesNotFound（兩族皆無線 / taught 定位失敗）、
    TaughtParamsError（由呼叫端在解析 taught JSON 時先行引發）。

    `cfg.line_find_method` 分流兩條找線路徑，最後收斂到同一個
    InspectResult 建構：
      "projection"（預設，亮線，50k 片型）：既有投影法，兩階段（先兩族
        幾何+找線、框邊配對法交叉驗證、再斷點偵測）。交叉驗證只在
        roi.mode != "Manual" 時跑（Manual ROI 不保證對齊實體黑框），
        teach() 不跑（教導本身有操作員目視確認）。
      "edge_pairing"（暗線，Ctype 片型）：見 edge_lines.py，主要找線法
        本身內建配對不出來就回 DetectionAnomaly 的硬性檢查，只服務
        inspect()，teach() 不支援。
    """
    roi_rect = resolve_roi(gray, roi, cfg)
    angles = estimate_angles(gray, roi_rect, cfg)

    angle_deg = placement_angle(angles)
    if abs(angle_deg) > float(angle_tol_deg):
        return PlacementResult(angle_deg=round(angle_deg, 3),
                               roi_used=roi_rect)

    if cfg.line_find_method == "edge_pairing":
        result = edge_lines_mod.inspect_edge_pairing(gray, roi_rect,
                                                      angle_deg, cfg)
        if isinstance(result, DetectionAnomaly):
            return result
        fam_details, defects_out, lines_total = result
        mode = "edge_pairing"
    else:
        thresholds = Thresholds.from_config(cfg)
        if taught is not None:
            thresholds = thresholds.merged_with(
                taught.thresholds.to_json_dict())
        mode = "taught" if taught is not None else "discovery"

        # 第一階段：兩族幾何 + 找線
        geoms = {}
        line_results = {}
        for ax in FAMILY_AXES:
            geoms[ax] = build_family_geometry(gray, ax, angles[ax], roi,
                                              roi_rect, cfg)
            line_results[ax] = find_family_lines(geoms[ax], cfg, taught)

        v_count = len(line_results["v"]["positions"]) if line_results["v"] else 0
        h_count = len(line_results["h"]["positions"]) if line_results["h"] else 0
        if v_count == 0 and h_count == 0:
            raise LinesNotFound("no cut lines found on any axis")

        # 交叉驗證的前提是 roi_rect＝大黑框內緣（AutoFrame / AutoInRoi
        # 皆為重新鎖框後的結果）；Manual 模式的 roi_rect 是操作員任意
        # 畫的矩形，不保證邊界對齊實體黑框，線不見得會乾淨地切過矩形
        # 邊緣，套用框邊配對法沒有物理意義，故不驗證。
        if roi.mode != "Manual":
            anomaly = crossval_mod.cross_validate(
                gray, roi_rect, round(angle_deg, 3), v_count, h_count, cfg)
            if anomaly is not None:
                return anomaly

        # 第二階段：斷點偵測（交叉驗證通過才做）
        defects_out = []
        fam_details = []
        lines_total = 0
        for ax in FAMILY_AXES:
            res = line_results[ax]
            if res is None:
                continue
            geom = geoms[ax]
            id_start = lines_total
            fam_defects = detect_family_breaks(geom, res["positions"],
                                               thresholds, id_start)
            defects_out.extend(fam_defects)
            n = len(res["positions"])
            lengths = [0.0] * n
            for d in fam_defects:
                lengths[d.line_id - id_start - 1] += d.length_px
            lines_total += n
            fam_details.append(_family_detection_from(geom, res, lengths))

    return InspectResult(
        verdict=Verdict.NG if defects_out else Verdict.OK,
        angle_deg=round(angle_deg, 3),
        lines_found=lines_total,
        defects=defects_out,
        roi_used=roi_rect,
        detection_mode=mode,
        families=fam_details)


def teach(gray: np.ndarray, cfg: AlgoConfig, roi: RoiSpec,
          angle_tol_deg: float = 5.0, image_name: str = ""):
    """教導（發現式）。回傳 TeachResult 或 PlacementResult。
    image_name 僅寫入 reference 供追溯；核心不碰檔案系統。"""
    roi_rect = resolve_roi(gray, roi, cfg)
    angles = estimate_angles(gray, roi_rect, cfg)

    angle_deg = placement_angle(angles)
    if abs(angle_deg) > float(angle_tol_deg):
        return PlacementResult(angle_deg=round(angle_deg, 3),
                               roi_used=roi_rect)

    thresholds = Thresholds.from_config(cfg)
    families = []
    fam_details = []
    for ax in FAMILY_AXES:
        geom = build_family_geometry(gray, ax, angles[ax], roi, roi_rect, cfg)
        res = find_family_lines(geom, cfg, taught=None)
        if res is None:
            continue
        families.append(_family_params_from(geom, res))
        fam_details.append(_family_detection_from(geom, res))

    if not families:
        raise LinesNotFound("teach: no cut lines found")

    taught = TaughtParams(
        families=families,
        thresholds=thresholds,
        reference={
            "taught_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "image": image_name,
        })
    return TeachResult(angle_deg=round(angle_deg, 3),
                       roi_used=roi_rect,
                       taught=taught,
                       families=fam_details)
