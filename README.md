# VisionEngine —— 陶瓷片切割線斷線檢測（Phase 1 MVP）

文件導覽：**ARCHITECTURE.md**（架構、合約、開發流程——動程式前必讀）、
PROTOCOL.md（TCP 協定規格）、BUILD.md（打包部署）、CLAUDE.md（AI 工具入口）。

三層結構（調機與生產共用同一份演算法）：

```
ve_core/     純演算法函式庫（無 I/O / UI / 網路），輸入 ndarray、輸出 dataclass
ve_server/   TCP JSON 薄殼（PROTOCOL.md），生產模式供 LabVIEW 呼叫
ve_ui/       調機工具（PySide6），分段快取即時調參；永久以原始碼執行
tests/       pytest：golden 特徵化 + 單元 + session 快取測試
```

## 環境建置（Windows，機台既有 Python 3.6 絕對不可動）

```bat
py -3.13 -m venv venv
venv\Scripts\pip install -r requirements-ui.txt   REM 生產機只裝 requirements.txt
```

## 執行

```bat
REM 調機工具（可帶影像路徑直接開圖）
venv\Scripts\python -m ve_ui.app [D:\images\piece_001.png]

REM 生產 server（LabVIEW 主程式以 System Exec 啟動）
venv\Scripts\python -m ve_server.main
venv\Scripts\python -m ve_server.main --mock      REM LabVIEW 離線開發

REM 測試（重要：server 程式碼變更後必跑，含 \r\n 行尾特徵化）
venv\Scripts\python -m pytest tests -q
```

## 調機工具操作流程

1. 載入影像 → 自動以「檢測（發現式）」跑一次並疊圖
2. 調參：**斷線門檻滑桿毫秒級即時重繪**；ROI/角度/找線參數會觸發
   對應階段以下的重算（秒級，狀態列顯示）
3. 教導：切「教導」模式 → 疊圖目視確認線數/角度/間距 →
   「接受教導→存檔」產出 taught_params.json（**即生產凍結格式**，
   之後由 LabVIEW 原樣搬進 Recipe）→ 自動切「檢測（驗證式）」
4. 批次資料夾 → 匯出結果：`*.json`（完整參數+結果，可重現）、
   `*_images.csv` / `*_defects.csv`（utf-8-sig，Excel 直開）

## 開發規則（凍結）

- 演算法一律進 ve_core；ve_ui / ve_server 不得含演算法
- ve_core 公開輸出一律**原圖座標**；去旋轉座標系不外漏
- taught_params JSON 鍵集合凍結（tests/test_characterization.py 釘死）
- server 程式碼變更重啟後必驗行尾 `\r\n`（tests 內建 TCP 驗證邏輯，
  或跑 test_client.py）
- 生產最終判定 = LabVIEW Judge；ve_core.reference_judge 僅供調機顯示

## 待辦（Phase 1 退出條件對照）

- [ ] 對照影像（已知切穿 vs 未切穿）到手後：門檻定量分析（退出條件 1）
- [ ] 實圖批次驗證 ±5° 找線穩定性（退出條件 2）——工具已備
- [x] 教導流程全程跑通（退出條件 3）
- [x] 3840x2748 全流程 < 2s（退出條件 4，實測約 1.0-1.1s 含載圖）
- [x] 放置異常與斷線 NG 區分（退出條件 5）
- [ ] 無切割線片型自動鎖框（退出條件 6）——**已知缺口**：平坦雜訊
      影像上發現式會回垃圾線而非報錯，需配方層旗標或週期性強度門檻
      （見 tests/test_core_units.py 的 pinned test）
- [x] taught_params JSON = 生產格式並凍結（退出條件 7）
