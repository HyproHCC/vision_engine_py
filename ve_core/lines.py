# -*- coding: utf-8 -*-
"""切割線位置偵測（在去旋轉座標系中）。

已驗證：去旋轉後投影法可抓到間距穩定（樣本約 130 px pitch）的切割道。
流程：
1. 細亮脊線帶通前處理（原圖 − 大核模糊，夾正值）— 只留細尺度亮結構，
   寬亮街道與晶粒幾何（圓晶粒、方晶粒皆然）一起被抑制。跨料號的通用
   不變量：切割線是細亮線，寬街道/晶粒邊緣不是。
2. 沿線方向取「高分位數投影」— 對每個垂直於線的位置，取沿線方向的
   85 分位數亮度。比平均值更能凸顯「大部分透亮、少段被晶粒遮擋」的切割道，
   比最大值抗雜訊。
3. pitch 以峰間距中位數為主（直接找峰量測，不受自相關諧波誤判影響）；
   自相關法降為備援（找不到 ≥2 個峰時才用）。
4. 峰值偵測（最小間距 = pitch * ratio），再用量到的 pitch 收斂一次
   min_dist 重找峰，濾掉雜訊近鄰峰。

驗證式（Taught）模式不重新找線：直接用 taught positions 附近微調
（±pitch/4 內找局部峰），對抗片間微小平移。
"""
import cv2
import numpy as np

from .errors import LinesNotFound

DEFAULT_RIDGE_KERNEL_PX = 15
DEFAULT_MIN_PITCH_PX = 20


def _smooth(x: np.ndarray, k: int) -> np.ndarray:
    k = max(3, k | 1)
    kernel = np.ones(k) / k
    return np.convolve(x, kernel, mode="same")


def ridge_bandpass(gray: np.ndarray, kernel_px: int) -> np.ndarray:
    """細亮脊線帶通：原圖 − 大核模糊，只留正值。

    大核模糊估計局部背景（寬亮街道、晶粒幾何等低頻結構），原圖減去
    背景後只剩細尺度亮結構（切割線）；負值（暗結構）夾為 0。
    kernel_px 需大於預期線寬，讓線本身被模糊「拉平」進背景而被扣除；
    太大會把半週期的晶粒結構也當成背景漏進來（配方層可調）。
    """
    k = max(3, int(kernel_px) | 1)
    src = gray.astype(np.float32)
    background = cv2.blur(src, (k, k))
    ridge = src - background
    np.clip(ridge, 0, None, out=ridge)
    return ridge


def line_profile_projection(rot_gray: np.ndarray, axis: str,
                            q: float = 85.0) -> np.ndarray:
    """垂直於線族方向的位置 → 沿線方向 q 分位數亮度。
    axis='v'：線近垂直 → 對每個 x 取該 column 的分位數。"""
    if axis == "v":
        return np.percentile(rot_gray, q, axis=0).astype(np.float64)
    return np.percentile(rot_gray, q, axis=1).astype(np.float64)


def estimate_pitch(proj: np.ndarray, min_pitch: int = 20) -> float:
    """自相關法估 pitch（備援：僅在峰間距法找不到 ≥2 個峰時使用）。"""
    x = proj - proj.mean()
    n = len(x)
    ac = np.correlate(x, x, mode="full")[n - 1:]
    ac[:min_pitch] = -np.inf  # 排除零延遲附近
    # 取搜尋範圍內「最大的局部峰」（第一個局部峰易被邊緣諧波/雜訊騙走）
    upper = min(len(ac) - 2, n // 2)
    best = -np.inf
    best_lag = 0
    for lag in range(min_pitch, upper):
        if ac[lag] > ac[lag - 1] and ac[lag] >= ac[lag + 1] and ac[lag] > best:
            best = ac[lag]
            best_lag = lag
    if best_lag == 0:
        raise LinesNotFound("pitch estimation failed (no periodicity)")
    # 最大峰可能落在 2x/3x 基本週期：檢查其約數位置是否也有可比的峰
    for div in (4, 3, 2):
        cand = best_lag // div
        if cand >= min_pitch and best_lag % div <= div:
            lo, hi = max(min_pitch, cand - 2), min(upper, cand + 3)
            if hi > lo and np.max(ac[lo:hi]) > 0.6 * best:
                return float(lo + int(np.argmax(ac[lo:hi])))
    return float(best_lag)


def find_peaks(proj: np.ndarray, min_dist: int, mad_k: float = 6.0) -> list:
    """簡單峰值偵測：局部最大 + 突出度門檻（中位數 + k * 穩健標準差）。

    用 MAD（中位絕對偏差，經 1.4826 換算近似標準差）而非 90 分位數：
    細亮脊線帶通後線本身在剖面中是稀疏尖峰（寬街道間距 130px 中線只佔
    ~9px），90 分位數容易還是落在背景雜訊上、門檻太低而讓背景雜訊起伏
    誤判為峰；MAD 只看多數背景樣本的離散程度，不受少數尖峰拉動，
    對稀疏尖峰訊號更穩健。"""
    sm = _smooth(proj, max(3, min_dist // 8))
    med = np.median(sm)
    mad = np.median(np.abs(sm - med)) * 1.4826
    prom_th = med + max(mad, 1e-9) * mad_k
    peaks = []
    for i in range(1, len(sm) - 1):
        if sm[i] >= sm[i - 1] and sm[i] > sm[i + 1] and sm[i] > prom_th:
            if peaks and i - peaks[-1] < min_dist:
                if sm[i] > sm[peaks[-1]]:
                    peaks[-1] = i
            else:
                peaks.append(i)
    return peaks


def refine_peak(proj: np.ndarray, pos: float, halfwin: int) -> float:
    """在 taught 位置附近找局部峰（驗證式模式的微調）。"""
    lo = max(0, int(round(pos)) - halfwin)
    hi = min(len(proj), int(round(pos)) + halfwin + 1)
    if hi <= lo:
        return pos
    return float(lo + int(np.argmax(proj[lo:hi])))


def _spacing_dispersion(diffs: np.ndarray) -> float:
    """相鄰峰間距的離散度：MAD/中位數。用 MAD（而非 std/mean）對 ROI
    邊緣造成的少數離群間距穩健——真週期訊號的間距應高度一致（趨近 0），
    子週期假峰摻雜時間距忽長忽短，離散度明顯偏高。"""
    diffs = np.asarray(diffs, dtype=np.float64)
    med = np.median(diffs)
    if med <= 0:
        return float("inf")
    mad = np.median(np.abs(diffs - med))
    return float(mad / med)


def _fill_pitch_gaps(proj: np.ndarray, peaks: list, pitch: float,
                     initial_peaks: list, min_pitch: int,
                     dispersion_th: float,
                     mad_k_gap: float = 4.5,
                     step_tol: float = 0.12,
                     match_win_ratio: float = 0.1,
                     max_gap_div: int = 16) -> tuple:
    """已知週期缺口內補找漏峰（h 族折半漏線，buglist 12）。

    根因：find_peaks 的平滑窗跟著 min_dist 走（min_dist//8），初始寬鬆
    偵測（k=3）抓得到的雙峰切割道，在 min_dist 收斂後（k=9 起）被重平滑
    壓低、剛好跌破 MAD 門檻——是漏峰不是子週期誤判。全域調低 mad_k
    已實驗否決（v 族雜訊復發），只能在「有規律週期佐證的缺口」內局部處理。

    作法：對相鄰峰間距 ≈ m×pitch（m≥2）的缺口，把缺口均分成 m 段，
    在每個預期位置 ±win 內依序用兩層標準採認漏峰：
      (1) 初始寬鬆偵測已找到的峰（已通過完整 mad_k 門檻，零新門檻）；
      (2) 初始平滑尺度下的局部極大值 + 局部放寬門檻（mad_k_gap，
          僅作用於缺口內，不動全域門檻）。
    pitch 假說一律先用呼叫端量到的最終 pitch；僅當最終峰集本身不規律
    （離散度 > dispersion_th，代表既有收斂/合併邏輯已失敗）才追加初始
    峰間距中位數當第二假說（處理整族折半、最終 pitch 量成雜訊值的情形）
    ——規律結果永遠不會被可能是子週期的初始 pitch 重切（保護 buglist 11
    的修復）。補完後整組間距離散度必須 ≤ dispersion_th，否則整批放棄：
    錯誤假說補出來的峰不會落在規律網格上，這是最後一道自檢。

    回傳 (pitch, peaks)；沒有可補的缺口或自檢不過時原樣返回。
    """
    if len(peaks) < 2 or pitch is None or pitch <= 0:
        return pitch, peaks
    diffs = np.diff(peaks)
    disp_final = _spacing_dispersion(diffs)

    hypotheses = [float(pitch)]
    if disp_final > dispersion_th and len(initial_peaks) >= 2:
        init_pitch = float(np.median(np.diff(initial_peaks)))
        if init_pitch >= min_pitch and init_pitch < 0.8 * pitch:
            hypotheses.append(init_pitch)

    sm = _smooth(proj, max(3, min_pitch // 8))
    med = np.median(sm)
    mad = np.median(np.abs(sm - med)) * 1.4826
    gap_th = med + max(mad, 1e-9) * mad_k_gap
    init_arr = np.asarray(initial_peaks, dtype=np.float64)

    best = None  # (disp_after, filled_peaks)
    for hyp in hypotheses:
        win = max(4.0, hyp * match_win_ratio)
        added = []
        for a, b in zip(peaks[:-1], peaks[1:]):
            gap = float(b - a)
            m = int(round(gap / hyp))
            if m < 2 or m > max_gap_div:
                continue
            step = gap / m
            if abs(step - hyp) > step_tol * hyp:
                continue
            for j in range(1, m):
                e = a + j * step
                cand = None
                # (1) 初始寬鬆偵測的峰（已通過完整門檻）
                if len(init_arr):
                    k = int(np.argmin(np.abs(init_arr - e)))
                    if abs(init_arr[k] - e) <= win:
                        cand = int(init_arr[k])
                # (2) 缺口內局部放寬門檻
                if cand is None:
                    lo = max(1, int(e - win))
                    hi = min(len(sm) - 1, int(e + win) + 1)
                    if hi > lo:
                        i = lo + int(np.argmax(sm[lo:hi]))
                        if (sm[i] >= sm[i - 1] and sm[i] > sm[i + 1]
                                and sm[i] > gap_th):
                            cand = i
                if cand is None:
                    continue
                # 與既有/已補峰保持最小間隔，避免重複或近鄰
                if min(abs(cand - q) for q in peaks) < 0.5 * hyp:
                    continue
                if added and min(abs(cand - q) for q in added) < 0.5 * hyp:
                    continue
                added.append(cand)
        if not added:
            continue
        filled = sorted(set(int(p) for p in peaks) | set(added))
        disp_after = _spacing_dispersion(np.diff(filled))
        if disp_after <= dispersion_th and (best is None or disp_after < best[0]):
            best = (disp_after, filled)

    if best is None:
        return pitch, peaks
    filled = best[1]
    return float(np.median(np.diff(filled))), filled


def estimate_pitch_from_peaks(proj: np.ndarray, min_pitch: int,
                              peak_min_dist_ratio: float = 0.6,
                              max_multiplier: int = 4,
                              dispersion_th: float = 0.15,
                              min_peaks_for_merge: int = 4) -> tuple:
    """直接找峰、用峰間距中位數當 pitch（主要方法，不受自相關諧波
    折回誤判影響）。回傳 (pitch, peaks)；峰數 < 2 時 pitch 為 None，
    呼叫端應退回 estimate_pitch 自相關備援。

    初始峰值偵測用寬鬆 min_dist（=min_pitch），容易被同一切割道內的
    晶粒邊緣/標記等細節分裂成數個子峰，真 pitch 被鎖到 1/2、1/3、1/4
    （症狀：找線數暴增，見 ARCHITECTURE.md §8「合成旋轉下找線數暴增」）。

    對策：先用量到的 pitch 收斂一次 min_dist 重找峰（既有行為，濾掉
    雜訊近鄰峰）。若間距仍不規律（離散度 > dispersion_th），疑似鎖到
    子週期，再把 min_dist 沿 pitch 的倍數（2x、3x、4x…）放大重找峰，
    挑離散度最低（最規律）的一級；候選峰數太少（< min_peaks_for_merge）
    時無法可靠評估離散度，直接跳過，避免把訊號稀疏的情形誤判成「更
    規律」而過度合併，把本來分開的真實相鄰線併掉。找不到更規律的候選
    時保留收斂後的原始峰——這個門檻同時保護「本來就正常」的案例不被
    誤動。

    最後一律過 _fill_pitch_gaps：min_dist 收斂會放大 find_peaks 的
    平滑窗，門檻邊緣的真實線峰可能被重平滑壓掉（h 族折半漏線，
    buglist 12），在 ≈ 整數倍 pitch 的缺口內把漏峰補回來。"""
    initial_peaks = find_peaks(proj, min_dist=min_pitch)
    if len(initial_peaks) < 2:
        return None, initial_peaks
    peaks = initial_peaks
    pitch = float(np.median(np.diff(peaks)))

    # 用量到的 pitch 收斂 min_dist，濾掉可能混進的雜訊近鄰峰後重找一次
    refined = find_peaks(proj, min_dist=max(min_pitch, int(pitch * peak_min_dist_ratio)))
    if len(refined) >= 2:
        peaks = refined
        pitch = float(np.median(np.diff(peaks)))

    diffs = np.diff(peaks)
    if len(peaks) >= min_peaks_for_merge and _spacing_dispersion(diffs) > dispersion_th:
        best_peaks, best_pitch = peaks, pitch
        best_disp = _spacing_dispersion(diffs)
        for m in range(2, max_multiplier + 1):
            min_dist = max(min_pitch, int(pitch * m * peak_min_dist_ratio))
            cand = find_peaks(proj, min_dist=min_dist)
            if len(cand) < min_peaks_for_merge:
                continue
            cand_diffs = np.diff(cand)
            disp = _spacing_dispersion(cand_diffs)
            if disp < best_disp:
                best_disp = disp
                best_peaks = cand
                best_pitch = float(np.median(cand_diffs))
                if best_disp <= dispersion_th:
                    break
        peaks, pitch = best_peaks, best_pitch

    return _fill_pitch_gaps(proj, peaks, pitch, initial_peaks, min_pitch,
                            dispersion_th)


def discover_lines(rot_gray: np.ndarray, axis: str,
                   peak_min_dist_ratio: float = 0.6,
                   ridge_kernel_px: int = DEFAULT_RIDGE_KERNEL_PX,
                   min_pitch: int = DEFAULT_MIN_PITCH_PX) -> dict:
    """發現式：細亮脊線帶通前處理 → 自動估 pitch 並找出所有線位置。"""
    ridge = ridge_bandpass(rot_gray, ridge_kernel_px)
    proj = line_profile_projection(ridge, axis)

    pitch, peaks = estimate_pitch_from_peaks(proj, min_pitch, peak_min_dist_ratio)
    if pitch is None:
        # 峰間距法找不到 ≥2 個峰（訊號太弱/太稀疏）才退回自相關備援
        pitch = estimate_pitch(proj, min_pitch)
        peaks = find_peaks(proj, min_dist=max(5, int(pitch * peak_min_dist_ratio)))

    if len(peaks) < 2:
        raise LinesNotFound("fewer than 2 lines found (axis=%s)" % axis)
    return {"positions": [float(p) for p in peaks], "pitch_px": pitch}


def verify_lines(rot_gray: np.ndarray, axis: str, taught_positions: list,
                 pitch_px: float,
                 ridge_kernel_px: int = DEFAULT_RIDGE_KERNEL_PX) -> dict:
    """驗證式：以 taught 位置為準，各自在 ±pitch/4 內微調（同一套細亮
    脊線帶通前處理，與教導時找到的峰對齊）。"""
    ridge = ridge_bandpass(rot_gray, ridge_kernel_px)
    proj = line_profile_projection(ridge, axis)
    halfwin = max(3, int(pitch_px / 4))
    positions = [refine_peak(proj, p, halfwin) for p in taught_positions]
    return {"positions": positions, "pitch_px": float(pitch_px)}
