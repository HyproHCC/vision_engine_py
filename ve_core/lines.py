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
    誤動。"""
    peaks = find_peaks(proj, min_dist=min_pitch)
    if len(peaks) < 2:
        return None, peaks
    pitch = float(np.median(np.diff(peaks)))

    # 用量到的 pitch 收斂 min_dist，濾掉可能混進的雜訊近鄰峰後重找一次
    refined = find_peaks(proj, min_dist=max(min_pitch, int(pitch * peak_min_dist_ratio)))
    if len(refined) >= 2:
        peaks = refined
        pitch = float(np.median(np.diff(peaks)))

    diffs = np.diff(peaks)
    if len(peaks) < min_peaks_for_merge or _spacing_dispersion(diffs) <= dispersion_th:
        return pitch, peaks

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
    return best_pitch, best_peaks


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
