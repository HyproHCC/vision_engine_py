# -*- coding: utf-8 -*-
"""VisionEngine server 設定。

設定檔 config.json 與 server.exe 同層（PyInstaller frozen 時取 exe 所在目錄）。
所有欄位皆有預設值，設定檔缺漏不會出錯。
"""
import json
import os
import sys

SERVER_VERSION = "1.0.0"

DEFAULTS = {
    "host": "127.0.0.1",
    "port": 5710,
    # NG 影像留存資料夾（相對路徑時以 base_dir 為準）
    "ng_dir": "ng",
    # NG 影像保留天數，超過由清理程序刪除；0 = 永不清理
    "ng_retention_days": 30,
    # 每次啟動與每次 inspect 後順手清理（輕量，掃一次資料夾）
    "cleanup_on_inspect": True,
    # log
    "log_dir": "logs",
    "log_level": "INFO",
    "log_max_bytes": 5 * 1024 * 1024,
    "log_backup_count": 10,
    # 影像規格（目前機台實際輸出；供手動修改，尚未接檢核邏輯）
    "expected_image": {
        "width": 3840,
        "height": 2748,
        "format": "PNG"
    },
    # 演算法預設（無 taught_params 時的發現式檢測用；教導後存進 taught_params）
    "algo": {
        # 大黑框/晶粒灰階上限與陶瓷區下限之間的分界（實測 黑~15-20 / 陶瓷~100-150）
        "frame_dark_max": 60,
        "ceramic_min": 90,
        # 去旋轉搜尋範圍與步進（deg）
        "angle_search_deg": 6.0,
        "angle_coarse_step": 0.5,
        "angle_fine_step": 0.05,
        # 找線：投影峰值最小間距佔估計 pitch 的比例
        "peak_min_dist_ratio": 0.6,
        # 找線前置細亮脊線帶通核尺寸（原圖-大核模糊後夾正值；配方層可調）
        "ridge_kernel_px": 15,
        # 剖面判定（待對照影像量化後定案 — 見 PROTOCOL.md 第 7 節）
        "cut_bright_thresh": 180,
        "min_break_len_px": 8,
        "band_halfwidth_px": 4,
        "gap_merge_px": 6,
        "edge_guard_px": 10,
        # 影像過大時演算法內部降採樣上限（估角度用；剖面分析仍用原解析度)
        "angle_est_max_side": 1400,
        # 框邊配對法交叉驗證（crossval.py）；待對照影像校準的暫定值
        "xval_inset_px": 40,
        "xval_edge_band_px": 4,
        "xval_angle_dispersion_tol_deg": 1.5,
        "xval_perp_tol_deg": 3.0,
        # 找線方法：projection（投影法，亮線，50k 片型）｜
        # edge_pairing（框邊配對法，暗線，Ctype 片型）
        "line_find_method": "projection"
    }
}


def base_dir() -> str:
    if getattr(sys, "frozen", False):  # PyInstaller
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _merge(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def load_config(path: str = None) -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy
    p = path or os.path.join(base_dir(), "config.json")
    if os.path.isfile(p):
        # 明確指定 utf-8：系統地區為 CP950，不能依賴預設編碼
        with open(p, "r", encoding="utf-8") as f:
            _merge(cfg, json.load(f))
    cfg["_config_path"] = p
    # 相對路徑正規化
    for key in ("ng_dir", "log_dir"):
        if not os.path.isabs(cfg[key]):
            cfg[key] = os.path.join(base_dir(), cfg[key])
    return cfg
