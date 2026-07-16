# VisionEngine 架構與開發指南

> 本文件的讀者是**維護者與 AI 開發工具**：重點是不變量、合約、依賴規則與「為什麼這樣設計」。
> 文件分工：README.md（入口與操作）、PROTOCOL.md（TCP 協定規格）、BUILD.md（打包部署）、本文件（架構與開發流程）。
> 中文一律使用台灣慣用語。

---

## 1. 系統定位與邊界

### 1.1 這是什麼

VisionEngine 是機台（V-cut 陶瓷劃片機）的視覺檢測子系統，判斷陶瓷片上的切割線是否有斷線（未切穿段）。目前為 Phase 1 MVP。

### 1.2 分工邊界

| 職責 | 負責方 |
|---|---|
| 機台控制、取像存檔、Recipe 管理、操作員介面 | LabVIEW 主程式 |
| 最終判定（verdict / Judge） | LabVIEW 主程式 |
| 影像檔 → 量測結果（線位、斷點、角度） | VisionEngine |
| 檢測結果 overlay 影像產出（**規劃中**，路徑由 inspect request 帶入，見第 9 節待辦） | VisionEngine |

- 影像一律以**檔案路徑**交換（如 `D:/VisionWork/`），不走記憶體或 socket 傳圖。取像寫檔由 LabVIEW 端負責。
- engine 只回報「觀測到的斷點」；小斷點是否放行由 LabVIEW Judge 依配方準則決定。`ve_core.reference_judge` 僅供調機工具顯示，**不得接進生產路徑**。

### 1.3 執行環境約束

- 同一台 Windows 機：LabVIEW 為 32-bit，engine 為獨立行程走 TCP（`127.0.0.1:5710`），不受位元數限制。
- **機台/開發機既有的系統 Python 3.6 絕對不可動**。理由：這台開發機上其他專案的 LabVIEW 以 Python Node 綁定系統 Python 3.6，升級或改動會破壞既有專案。VisionEngine 一律用自己的 venv（開發 3.13）或打包後的 ve_server.exe（3.11+ 64-bit 打包）。
- 影像規格：3840×2748、PNG，可由 `config.json` 的 `expected_image` 區（`width`/`height`/`format`）調整；目前僅供設定，尚未接檢核邏輯。

### 1.4 三個執行角色

| 角色 | 執行形式 | 使用者 |
|---|---|---|
| ve_ui 調機工具 | 永久以原始碼執行，不打包 | 工程師調整參數 / 教導 |
| ve_server 生產 | PyInstaller 單檔 exe，LabVIEW System Exec 啟動 | 產線（LabVIEW 呼叫） |
| tests | pytest | 開發時 |

### 1.5 範圍與非目標（Phase 1）

- 單一 client、一問一答循序處理，無並行需求。
- engine 不做最終 Judge。
- **AutoFrame 為非核心、暫緩**：生產流程以人工拉 ROI（Manual）為主，AutoFrame 只留作調機輔助；對圓晶粒＋寬街道片型的失效不再追（見 8）。
- 實際片型的切割線**一律縱橫雙向**。程式碼容忍單方向片型（taught 中無該 axis 回 None），但這是未經實圖驗證的容忍行為，非需求，不做相容承諾。

---

## 2. 三層架構與依賴規則（凍結）

### 2.1 分層總覽

```
ve_ui (PySide6 調機)   ve_server (TCP 薄殼)     ← 兩者互不相依
        ↘                ↙
         ve_core (純演算法：ndarray 進、dataclass 出)
              ↓ 只依賴 numpy / cv2 / 標準庫
```

tests/ 直接測 ve_core 與 ve_ui/session；test_client.py 測 server 端到端。

### 2.2 凍結規則與理由

| 規則 | 理由 |
|---|---|
| 演算法一律進 ve_core，ve_ui / ve_server 不得含演算法 | 調機與生產跑**同一份程式碼**——調機工具看到的結果就是產線行為；演算法散落兩處必然分歧 |
| ve_core 無 I/O / UI / 網路 | 可純函式單元測試與 golden 特徵化；不純的部分集中管理（見 2.3） |
| ve_core 對外一律**原圖座標**，去旋轉座標系不外漏 | LabVIEW overlay 與 UI overlay 直接畫、零自寫換算；座標換算 bug 只可能發生在一個地方（derotate.py） |
| ve_ui 與 ve_server 不得互相 import | 生產打包（PyInstaller）不得拖進 Qt；調機工具也不依賴 server 存活 |
| ve_ui/session.py 無 Qt 相依 | 調機執行核心可獨立 pytest |

### 2.3 「不純」邊界對照表

新增任何副作用（讀寫檔、網路、log）時照表歸位：

| 副作用 | 歸屬 |
|---|---|
| 生產側讀圖、NG 留存、ve_core 例外 → error_code | ve_server/engine.py |
| log 設定 | ve_server/logsetup.py |
| 調機側讀圖（含中文路徑處理） | ve_ui/loader.py |
| 結果與參數匯出（JSON / CSV） | ve_ui/export.py |
| （規劃中）overlay 影像繪製與存檔 | ve_server/engine.py（見 5.4） |

---

## 3. ve_core 檢測管線

### 3.1 管線流程

```
resolve_roi        原圖 ROI（Manual 裁切驗證 / AutoFrame 鎖框 / AutoInRoi 粗框內精確找內緣）
estimate_angles    兩族 v/h 各自估角（於 ROI 內）
placement check    |角度較大者| > angle_tol → PLACEMENT_ERROR，直接返回
對每族 ax ∈ {v, h}：
  build_family_geometry  整張圖去旋轉 + 在旋轉座標系內「重新定位」分析區
  find_family_lines      有 taught → verify（驗證式）／無 taught → discover（發現式）
兩族皆無線 → LinesNotFound
[僅 inspect()] 框邊配對法交叉驗證（crossval.cross_validate，roi_rect
  在 Manual 模式時跳過）→ 沒過直接回 DetectionAnomaly，不做斷點偵測
對每族 ax ∈ {v, h}：
  detect_family_breaks   沿線剖面找斷點 → 座標映回原圖；順帶算出
                          break_lengths_px（每線總斷線長度，需求 6）
InspectResult：verdict = 有 defects 則 NG，否則 OK
```

`inspect()` / `teach()` 是上述階段的組合；ve_server 與批次測試直接用。
交叉驗證只在 `inspect()` 跑，`teach()` 不驗證（教導本身有操作員目視確認）。

### 3.2 設計決策（改程式前必讀）

| 決策 | 理由 |
|---|---|
| 每族**旋轉整張影像**後重新定位分析區（Manual 取旋轉後內接矩形、AutoFrame 重跑鎖框） | 消除軸對齊 ROI 在旋轉影像上包進框角/邊緣過渡帶造成的**假線**——已驗證行為，不可改回「只轉 ROI」 |
| v/h 兩族完全獨立（各自估角、去旋轉、找線） | 兩族角度允許些微不同；單方向片型路徑見 1.5 |
| discovery 找不到線＝軟失敗（該族回 None）；taught verify 失敗＝硬錯誤 LinesNotFound | 發現式本來就在探索；驗證式失敗代表片況與教導不符，必須報錯 |
| thresholds 合併順序：config 預設 ← taught.thresholds 覆蓋（taught 內出現的鍵才覆蓋） | 教導時凍結的門檻優先於機台 config |
| line_id 跨族連續編號，由呼叫端累計 | defects 表格全域唯一 id |
| placement 檢查在找線**之前**，提前返回 | 放置異常時找線結果無意義，也省時間 |
| 切割線在實機影像上是暗線；`pipeline.find_family_lines`/`detect_family_breaks` 內部把 `geom.sub` 反相（`_dark_line_view`，`255-x`）後才交給既有的「亮線」演算法（`ridge_bandpass`/`band_profile`/`find_dark_runs` 皆不改） | 唯一反相入口，同時對 discovery/taught/inspect/teach 生效；`lines.py`/`breaks.py`/`profile.py` 內部邏輯與既有單元測試不受影響 |
| 框邊配對法交叉驗證（`crossval.py`）只在 `roi.mode != "Manual"` 時跑 | 前提是 roi_rect＝大黑框內緣（AutoFrame/AutoInRoi 皆為重新鎖框後的結果）；Manual ROI 是操作員任意矩形，邊界不保證對齊實體黑框，線不見得乾淨切過矩形邊緣，套用框邊配對法沒有物理意義 |
| 交叉驗證的谷點/線數一致性檢查（reason `COUNT_MISMATCH_*`）容許 ±1 | peak 判準要求兩側鄰居都存在，最外側那條線的谷點若剛好落在剖面陣列頭尾，結構上就測不到，跟真的漏偵測是兩回事 |

### 3.3 座標系合約（全專案最重要的不變量）

三個座標系：

```
原圖 --(M)--> 旋轉座標 --(減 region 原點)--> 分析區座標
```

- 對外輸出**只有原圖座標**（BreakDefect、roi_used、overlay 線段）。
- 反向換算唯一入口：`derotate.map_points_back`（經 `Minv`）。整條線映回原圖用 `pipeline.map_line_to_original`。
- **taught `positions_px` 的定義＝該族去旋轉座標系中、以分析區原點為基準的線位置**（自 tp_version=1 起凍結）。隱含前提：教導與檢測的 ROI 給法必須一致，否則整組線位偏移。

### 3.4 分段 API 成本表

管線拆成可個別呼叫的階段函式（成本為 3840×2748 實測量級）：

| 階段函式 | 成本 | 什麼變動時要重跑 |
|---|---|---|
| `resolve_roi()` | 便宜 | ROI 參數 |
| `estimate_angles()` | 貴（秒級） | 角度搜尋參數 |
| `build_family_geometry()` | 貴（每族一次） | 角度或 ROI |
| `find_family_lines()` | 中 | 找線參數 / taught |
| `detect_family_breaks()` | 便宜（毫秒） | 斷線門檻 |

這張表是 6.2 session 快取失效邏輯的依據。**在管線新增參數時，必須同時決定它屬於哪一段**，並更新 session 的失效對照（見 6.2），否則會出現「調了參數畫面沒反應」的 bug。

### 3.5 模組一覽

| 模組 | 職責 |
|---|---|
| frame.py | 大黑框內緣定位（AutoFrame / AutoInRoi 共用 find_inner_roi） |
| derotate.py | 旋轉角估計、rotate_keep_center、座標正反轉換 |
| lines.py | 找線：discover（發現式）/ verify（驗證式），含細亮脊線帶通前置 |
| profile.py | 沿切割道的剖面萃取 |
| breaks.py | 剖面斷點偵測（去旋轉座標系內） |
| crossval.py | 框邊配對法交叉驗證（獨立於投影找線法之外的第二道把關，僅 inspect() 用） |
| judge.py | 參考 Judge，僅供調機顯示 |
| pipeline.py | 階段組合、座標映回、inspect/teach |
| types.py | 資料合約 + TP_VERSION（JSON 序列化與 PROTOCOL.md 一一對應且凍結） |
| errors.py | 例外階層；ve_core 不知道協定 error code，映射在 ve_server/engine.py |

---

## 4. taught_params 生命週期

### 4.1 生命週期（一條單行道）

```
ve_ui 教導（發現式 teach）
 → 「接受教導→存檔」產出 taught_params.json（此格式＝生產凍結格式）
 → 人工交付 → LabVIEW 原樣存入 Recipe（不解析、不改動任何位元組）
 → 生產時 inspect request 的 taught_params 欄位原樣帶回 engine
 → engine 解析為 TaughtParams dataclass → 驗證式檢測
```

**LabVIEW 從頭到尾不解析這個 JSON**——schema 演進 LabVIEW 端零改動；engine 是唯一讀寫者，格式責任全在 Python 側。

### 4.2 凍結與演進規則

| 項目 | 規則 |
|---|---|
| 鍵集合 | 凍結，`tests/test_characterization.py` 釘死；改鍵＝測試紅燈 |
| `positions_px` 語意 | 自 v1 凍結（見 3.3） |
| 改 schema 的唯一合法程序 | ① 遞增 `TP_VERSION`（types.py） ② 同步改 PROTOCOL.md §7 ③ 更新特徵化測試 ④ 舊版 tp 的相容策略明寫（拒收或升級） |

### 4.3 三層參數的關係

| 參數層 | 載體 | 層級 | 生效方式 |
|---|---|---|---|
| AlgoConfig | config.json `algo` 區 | 機台級預設 | 發現式檢測直接用 |
| taught_params | Recipe（LabVIEW 保管） | 片型級 | 驗證式：`thresholds` 內**出現的鍵覆蓋**預設，未出現的用預設 |
| UI 即時調參 | 調機 session 記憶體 | 暫時 | 只存在調機過程，「接受教導」才落地 |

注：`ridge_kernel_px`（細亮脊線帶通核尺寸）目前為機台級 config，是否配方化（存入 taught_params）已暫緩，見第 9 節。

---

## 5. ve_server 分層

### 5.1 各檔職責（依請求流動順序）

```
main.py       進入點：參數（--mock / --port）、config 載入、log 初始化
server.py     TCP 主迴圈：單一連線、逐行收發
protocol.py   訊息解析/驗證/回應組裝——與 PROTOCOL.md 一一對應
dispatcher.py 指令分派（ping/inspect/teach/shutdown）＋ mock 實作＋ NG 定期清理
engine.py     協定 ↔ ve_core 轉接層：所有「不純」集中地
              （讀圖、NG 留存、ve_core 例外→error_code、dataclass→協定 dict）
config.py     config.json 載入，缺漏欄位用內建預設
logsetup.py   rotating log，一律 UTF-8（CP950 寫入例外教訓）
```

### 5.2 必守不變量

| 不變量 | 出處 / 理由 |
|---|---|
| 行尾固定 `\r\n`，統一由 `protocol.encode_response` 產生 | LabVIEW TCP Read CRLF 模式遇到只有 `\n` 會**靜默失敗**——歷史教訓，重新打包後必實測（BUILD.md 必驗項） |
| 回應 `ensure_ascii=True`；client 字串欄位僅允許 ASCII，違者 error 122 | CP950 環境的編碼地雷一律擋在協定邊界 |
| 單一連線、一問一答循序；`request_id` 原樣回填 | LabVIEW 200ms 輪詢模型的前提 |
| mock 模式**不 import cv2** | LabVIEW 端可在無 OpenCV 環境離線開發；mock verdict 三態輪替（OK/NG/PLACEMENT_ERROR） |
| 例外 → error_code 映射只發生在 engine.py（100–110）與 protocol 層（120–122） | ve_core 不知道協定 code（errors.py 檔頭明文） |

### 5.3 細節參照

錯誤碼表：PROTOCOL.md §9。傳輸層規格：PROTOCOL.md §1。打包與重打包後三項必驗：BUILD.md。

### 5.4 overlay 影像功能掛鉤（規劃中）

第 1 節定案的 overlay 影像存檔：繪圖與存檔屬「不純」，實作歸位 engine.py；演算法端 `pipeline.map_line_to_original` 已備好線段映射。協定需在 inspect request 新增路徑欄位（PROTOCOL.md 改版），見第 9 節待辦。

---

## 6. ve_ui 與 InspectionSession

### 6.1 檔案職責

| 檔案 | 職責 |
|---|---|
| app.py | 進入點：`python -m ve_ui.app [影像路徑]` |
| main_window.py | 主視窗組裝與事件接線 |
| param_panel.py | 參數面板，依管線階段分組 |
| image_view.py | 縮放平移＋多層 overlay（**皆原圖座標，零自寫換算**） |
| results_panel.py | 斷點表格＋線族摘要＋各階段耗時 |
| session.py | InspectionSession——分段快取執行核心，無 Qt 相依 |
| batch.py | 批次測試：資料夾內全部影像以目前參數執行完整檢測 |
| export.py | JSON / CSV 匯出 |
| loader.py | 讀圖（含中文路徑處理） |

### 6.2 dirty-level 快取模型

```
S_ROI(0) → S_ANGLE(1) → S_GEOM(2) → S_LINES(3) → S_BREAKS(4) → S_CLEAN(99)
```

參數變動呼叫 `_invalidate(level)`，dirty 只會往**上游**推（取 min）；`run()` 從 dirty 階段往下游重算、上游快取沿用。觸發對照表：

| 變動 | 失效至 |
|---|---|
| 斷線門檻滑桿、judge 參數 | S_BREAKS（毫秒級，「即時重繪」的本體） |
| 找線參數、切換模式、換 taught | S_LINES |
| angle_tol | S_GEOM |
| 角度搜尋參數 | S_ANGLE |
| ROI、換影像 | S_ROI（全重算） |

**行為守則：新增任何演算法參數時，必須同時決定它屬於哪個 group、失效到哪一層**（呼應 3.4）。漏做的症狀是「調了參數畫面沒反應」。

刻意設計（不是 bug）：placement 超差時 session 把 dirty 停在 S_GEOM，之後放寬 angle_tol 可從 GEOM 續跑，不必重新估角。

### 6.3 三種模式與兩個判定欄位

- 模式：`discovery`（發現式）／`taught`（驗證式）／`teach`（教導＝發現式＋產出 TaughtParams 供目視確認）。
- `SessionResult.engine_status`（引擎原始結論 OK/NG/PLACEMENT_ERROR）與 `SessionResult.verdict`（過參考 Judge 後的顯示用判定）是**兩個欄位**。verdict 僅 MVP 顯示用，生產判定在 LabVIEW——不得把 reference_judge 接進生產路徑。

### 6.4 UI 側地雷

- loader：CP950 環境下 cv2.imread 對中文路徑會**靜默回 None**，故走 np.fromfile 繞路。
- export：CSV 一律 utf-8-sig（帶 BOM），CP950 地區 Excel 直接雙擊可開。
- overlay 疊圖一律原圖座標。

操作步驟教學（載圖→調整參數→教導→批次匯出）見 README.md。

---

## 7. 開發流程

| 環節 | 內容 |
|---|---|
| 開發環境 | 開發機台直接測試；此機另有專案的 LabVIEW 綁定系統 Python 3.6，**不可動**（見 1.3） |
| 實圖來源 | 原機台取像下載，統一放 `vision_engine_py/testdata/`（已 .gitignore，不進版本庫）；新片型影像先進調機工具用發現式看結果 |
| 改程式後必跑 | `venv\Scripts\python -m pytest tests -q`；動到 ve_server 的加跑 `test_client.py` 實測行尾 |
| 變更類型 × 驗證 | 演算法 → 單元＋golden 特徵化；協定/server → 特徵化＋test_client.py；UI → session 測試＋手動操作 |
| golden 重錄時機 | 只有「演算法行為**刻意**改變」才重錄（`tests/record_golden.py`）；重錄前先確認與舊行為的差異是預期的 |
| 凍結項變更 | taught_params 動 schema 走 4.2 的四步驟程序 |
| 打包與部署 | 見 BUILD.md，含重新打包後三項必驗 |
| 日常驗證 | **Python 端為主**：pytest ＋ test_client.py（mock 或實圖）就足夠，MVP 階段不動用 LabVIEW |
| LabVIEW 端對端實測 | **後期整合階段才做**（MVP 演算法驗收完、要正式與主程式對接時）：LabVIEW 實際發指令、收回應、畫 overlay 跑一輪。之後每次交付新 ve_server.exe 給主程式前做一輪 |

### 版本控制紀律（git）

- 倉庫位置：`Code/AI/claude/`（含 buglist.txt 與 vision_engine_py）。
- **pytest 全綠才 commit**。
- **每次打包 ve_server.exe 就打一個 tag**（如 `v1.0.0-build3`），機台上跑的 exe 永遠對得回原始碼。
- `.gitignore` 已排除 venv、__pycache__、logs、ng、打包產物。

---

## 8. 已知陷阱與演算法教訓

每條都是踩過的雷，格式：症狀 → 原因 → 對策。

| 教訓 | 症狀 → 原因 → 對策 |
|---|---|
| CP950 中文路徑 | cv2.imread **靜默回 None** → OpenCV 不吃非 ASCII 路徑 → loader 走 np.fromfile；log 一律 UTF-8；CSV 用 utf-8-sig；協定字串欄位只收 ASCII |
| LabVIEW TCP 行尾 | 收不到回應但無錯誤 → CRLF 模式遇 `\n` 靜默失敗 → `\r\n` 統一由 encode_response 產生；重新打包必實測 |
| pitch 諧波折回（buglist 1、9） | 線數翻倍（例：21 條）→ 晶粒半週期強峰讓自相關誤把真 pitch 當二次諧波折半 → pitch 改**峰間距中位數**主導，自相關降為備援 |
| 投影抓錯結構（buglist 2） | 找線結果落在切割線兩側或消失 → q85 投影在寬亮街道整段飽和，剖面被晶粒幾何主導 → 前置「細亮脊線帶通」：原圖 − 大核模糊後夾正值，只留細尺度亮結構（切割線是細亮線＝跨料號通用不變量）。k=15 實圖驗證有效、k=31 開始漏進半週期結構 |
| AutoFrame 失效片型 | 圓晶粒＋寬街道片型鎖不到框 → 平坦雜訊假設不成立 → 已降級非核心（1.5），生產用 Manual ROI |
| 教導/檢測 ROI 一致性 | 驗證式整組線位偏移 → taught positions_px 以分析區原點為基準（3.3） → 兩邊 ROI 給法必須一致 |
| pitch 鎖到子週期（2026-07-15，已修復並覆核，`a8d7b08`） | 合成旋轉重跑找線數暴增 2–3 倍，峰打在圓晶粒邊緣非切割街道（真 pitch≈128 被鎖到 1/4≈33） → 初始峰偵測 min_dist=20 遠小於真 pitch，晶粒邊緣細亮結構在同一街道內拆成多個緊鄰假峰，峰間距中位數被拉向子週期 → `lines.py::estimate_pitch_from_peaks`：峰間距離散度（MAD/中位數）>0.15 才沿 pitch 倍數（2x/3x/4x）放大 min_dist 重找峰、挑離散度最低一級；已規律或候選峰 <4 一律不動。修復後 v 族 pitch 兩批 8 張實圖全部收斂 127–128px。詳錄：buglist 11 |
| h 族折半漏線（待修，2026-07-15，已定位） | h 族 pitch 鎖到 ~2 倍（~276 vs 真 ~128）、線數剩 4–5 條 → 真實線峰初始偵測有抓到，但平滑後高度剛好卡 MAD 突出度門檻邊緣（隨角度重取樣微幅浮動），是**漏峰**而非子週期誤判，放大 min_dist 無效 → 全域調低 `mad_k`（6.0→4.5）**已試過並否決**：v 族雜訊復發更亂，已還原。安全方向：僅在已知 pitch 的 2x/3x 缺口內局部降門檻補找，未實作。詳錄：buglist 12 |

---

## 9. 現況快照（2026-07-15）

> 本節是唯一允許過期的一節；更新時改快照日期。
> **本節體重紀律**：待辦每項一行、附 § 或 buglist 指標；調查過程與輪次紀錄寫 buglist.txt 或 commit message，不寫在本檔；完成的待辦直接刪除（歷史在 git）。

### Phase 1 退出條件

| # | 條件 | 狀態 |
|---|---|---|
| 1 | 對照影像（已知切穿 vs 未切穿）門檻定量分析 | 待對照影像到手 |
| 2 | 實圖批次驗證 ±5° 找線穩定性 | **跑過三輪，仍未過**：估角誤差 ≤0.3°；v 族已修復並覆核（`a8d7b08`）；h 族折半漏線待修，暫緩待安全的局部修法（見 §8、buglist 11–12） |
| 3 | 教導流程全程跑通 | 完成 |
| 4 | 3840×2748 全流程 < 2s | 完成（實測約 1.0–1.1s 含載圖） |
| 5 | 放置異常與斷線 NG 區分 | 完成 |
| 6 | 無切割線片型自動鎖框（AutoFrame） | **改判：非核心、暫緩**（1.5） |

### 待辦

1. overlay 影像存檔：inspect request 帶路徑、PROTOCOL.md 加欄位、實作歸 engine.py（5.4）。
2. Manual ROI 改收 LabVIEW 格式（左、上、右、下），內部轉 x/y/w/h（buglist 既有項）。
3. 「套用 AutoFrame 結果為 Manual 起點」按鈕；find_inner_roi 的 frac / run_need 開放到面板（buglist 既有項）。
4. requirements-ui.txt 補 pytest（buglist 既有項）。
5. 對照影像到手後：門檻定量分析（退出條件 1）。
6. ±5° 穩定性（退出條件 2）：h 族折半漏線待修，根因與已否決的全域門檻修法見 §8，方向為已知週期缺口內局部降門檻（buglist 12）。
7. 次要待查：`cor` 校正版部分角度耗時 >2s（最高 3868ms），需無背景負載重測確認是否量測雜訊（退出條件 4）。

### 暫緩區（有明確再啟動條件）

| 項目 | 再啟動條件 |
|---|---|
| ridge_kernel_px 配方化（存入 taught_params，需 TP_VERSION→2） | 換片型實測發現機台級預設不夠用時 |
| AutoFrame 重新設計 | 收集到足夠失效樣本後 |
| 雙峰切割道找線穩健化（峰對合併取街道中心等） | 實圖確認雙峰形狀後定案 |
