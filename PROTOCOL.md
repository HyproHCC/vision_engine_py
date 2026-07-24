# VisionEngine TCP JSON 協定規格 v1.0

## 1. 傳輸層

- TCP，engine 為 server（預設 `127.0.0.1:5710`），LabVIEW 為 client，單一連線。
- 每則訊息為一行 JSON，**行尾固定 `\r\n`**（LabVIEW TCP Read CRLF 模式）。
- Server 送出的 JSON 一律 `ensure_ascii=True`（非 ASCII 字元轉 `\uXXXX`），實務上協定內容全 ASCII。
- Client 送出的字串欄位（檔名、路徑、piece_id、recipe_name）**只允許 ASCII**；LabVIEW 端 `ENG_Start.vi` 送出前強制檢查，engine 端收到非 ASCII 回 `error_code=122`。
- 一問一答、循序處理：client 送一行指令，engine 處理完回一行回應。LabVIEW 以 200ms TCP Read 輪詢，timeout(56) 視為 Pending。
- `request_id` 由 LabVIEW 發號（建議格式 `REQ-000123`），engine **原樣回填**。LabVIEW 收到不符的 request_id 應丟棄該行繼續等（error 5401 情境）。

## 2. 指令總覽

| cmd | 用途 | 典型耗時 |
|---|---|---|
| `ping` | 存活確認（Idle 心跳） | <10ms |
| `inspect` | 檢測一張影像 | <2s |
| `teach` | 教導模式：發現式偵測，回報量測參數 | <2s |
| `shutdown` | 回應後 server 自行結束 | <10ms |

## 3. 共通欄位

### Request（所有指令）
```json
{"request_id": "REQ-000123", "cmd": "inspect", ...}
```

### Response（所有指令）
```json
{
  "request_id": "REQ-000123",
  "cmd": "inspect",
  "status": "OK | NG | PLACEMENT_ERROR | DETECTION_ANOMALY | ENGINE_ERROR",
  "error_code": 0,
  "error_msg": "",
  "elapsed_ms": 843.2
}
```

- `status` 對應 LabVIEW `EngineResponse.ctl` 的 status enum（`ParseError` 為 LabVIEW 端自產，engine 不會送）。
- `error_code=0` 表示無引擎錯誤；非 0 時 `status` 必為 `ENGINE_ERROR`，LabVIEW 端映射為 user error 5402。

## 4. ping

Request:
```json
{"request_id": "REQ-000001", "cmd": "ping"}
```
Response:
```json
{"request_id": "REQ-000001", "cmd": "ping", "status": "OK",
 "error_code": 0, "error_msg": "", "elapsed_ms": 0.3,
 "server_version": "1.0.0", "mock": false, "uptime_s": 1234.5}
```

## 5. inspect

Request:
```json
{
  "request_id": "REQ-000123",
  "cmd": "inspect",
  "image_path": "D:/VisionWork/img_20260706_101500_001.png",
  "piece_id": "P20260706-001",
  "recipe_name": "TYPE_A",
  "roi_mode": "AutoFrame",
  "roi_rect": {"left": 0, "top": 0, "right": 0, "bottom": 0},
  "angle_tol_deg": 5.0,
  "param_source": "Taught",
  "taught_params": { ... 見第 7 節，教導時 engine 產出、LabVIEW 原樣搬運 ... }
}
```

- `roi_mode`: `"Manual"` 時使用 `roi_rect`（原圖座標）；`"AutoFrame"` 時 engine 自動定位大黑框內緣，忽略 `roi_rect`。
- `roi_rect` / `roi_used` 一律是 LabVIEW IMAQ 慣例的 Rectangle cluster：`{left, top, right, bottom}`，**座標值必須為整數**，且 **right/bottom 不含**（寬 = right − left、高 = bottom − top）。`roi_mode="Manual"` 時必須滿足 `right>left` 且 `bottom>top` 且所有座標欄位皆為整數，否則回 `error_code=122`。不保留舊 `{x, y, w, h}` 格式的相容。
- `param_source`: `"None" | "Taught" | "Manual"`。`Taught` 走驗證式檢測（用 `taught_params`）；`None` 退回發現式並在回應註記 `"detection_mode": "discovery"`。
- `taught_params`: JSON 物件。`param_source != "Taught"` 時可省略或給 `null`。

Response（正常判定，含 NG）:
```json
{
  "request_id": "REQ-000123",
  "cmd": "inspect",
  "status": "NG",
  "error_code": 0,
  "error_msg": "",
  "elapsed_ms": 843.2,
  "detection_mode": "taught",
  "angle_deg": 1.32,
  "lines_found": 24,
  "roi_used": {"left": 412, "top": 380, "right": 3422, "bottom": 2368},
  "defects": [
    {"line_id": 3, "x1": 1204.5, "y1": 812.0, "x2": 1204.5, "y2": 951.0, "length_px": 139.0},
    {"line_id": 7, "x1": 2110.0, "y1": 1433.5, "x2": 2251.0, "y2": 1433.5, "length_px": 141.0}
  ],
  "v_break_lengths_px": [0.0, 0.0, 139.0, 0.0, "... 每條 v 族線總斷線長度 ..."],
  "h_break_lengths_px": [0.0, 141.0, 0.0, "... 每條 h 族線總斷線長度 ..."],
  "ng_image_path": "D:/VisionWork/ng/img_20260706_101500_001.png"
}
```

- **defects 座標一律為原圖座標**（engine 負責去旋轉的反轉換），LabVIEW Overlay 直接用。
- `status="OK"` 時 `defects` 為空陣列。engine 只回報「觀測到的斷點」；小斷點是否放行由 LabVIEW Judge 依配方準則決定（engine 不做 Judge）。
  - 注意：engine 端 `status` 的 OK/NG 只是「有無偵測到斷點」的原始結論，**最終 verdict 由 LabVIEW Judge 產生**。
- `v_break_lengths_px` / `h_break_lengths_px`：與 `defects[]` 並存的簡化格式，兩個一維陣列，`[線序] = 該線總斷線長度(px)`，無斷線為 `0.0`；線序對應 `taught_params.families[axis=v/h].positions_px` 的順序（教導時的線序）。`PLACEMENT_ERROR` / `DETECTION_ANOMALY` 時固定回空陣列 `[]`（欄位一律存在、型別穩定，LabVIEW 端不必處理欄位缺席）。
- `ng_image_path`: 有 defects 時 engine 複製原圖到 NG 留存資料夾後回傳路徑；無則為 `""`。

Response（放置異常）:
```json
{"request_id": "...", "cmd": "inspect", "status": "PLACEMENT_ERROR",
 "error_code": 0, "error_msg": "", "elapsed_ms": 401.0,
 "angle_deg": 6.8, "lines_found": 0, "defects": [],
 "v_break_lengths_px": [], "h_break_lengths_px": []}
```
- `|angle_deg| > angle_tol_deg` 時回 `PLACEMENT_ERROR`，不進行找線與斷線判定。LabVIEW 端映射為 verdict=Placement（黃框提示），**不是** error cluster。

Response（檢測異常——框邊配對法交叉驗證沒過，reason_codes 對照表見下）:
```json
{"request_id": "...", "cmd": "inspect", "status": "DETECTION_ANOMALY",
 "error_code": 0, "error_msg": "", "elapsed_ms": 512.0,
 "angle_deg": 1.28, "lines_found": 0, "defects": [],
 "v_break_lengths_px": [], "h_break_lengths_px": [],
 "roi_used": {"left": 412, "top": 380, "right": 3422, "bottom": 2368},
 "detection_mode": "n/a",
 "reason_codes": ["COUNT_MISMATCH_V"]}
```
- 找線本身有結果，但與框邊配對法交叉驗證（獨立於投影找線法之外的第二道把關）互相矛盾，代表偵測結果本身不可信——**明確區分於「斷線 NG」**：NG 是「有偵測到斷點」，DETECTION_ANOMALY 是「這次偵測結果不採信」，不做斷點判定。只有 `roi_mode="Manual"` 以外的模式（AutoFrame / AutoInRoi）才會驗證；Manual ROI 不保證邊界對齊實體黑框，不套用此檢查。`teach` 不驗證（教導本身有操作員目視確認）。

`reason_codes` 對照表（同一次驗證可能同時出現多個）：

| reason code | 意義 |
|---|---|
| `ANGLE_DISPERSION_V` | v 族線各自角度（框邊配對法量測，非投影法角度）離散度超過容差 |
| `ANGLE_DISPERSION_H` | h 族同上 |
| `PERPENDICULARITY` | v/h 兩族代表角度夾角與 90° 相差超過容差 |
| `COUNT_MISMATCH_V` | 小方框上下邊谷點數與投影找線法找到的 v 族線數對不上（容許 ±1） |
| `COUNT_MISMATCH_H` | 小方框左右邊谷點數與投影找線法找到的 h 族線數對不上（容許 ±1） |
| `INSET_DEGENERATE` | 大黑框內緣往內縮後方框太小，無法驗證 |

Response（引擎錯誤）:
```json
{"request_id": "...", "cmd": "inspect", "status": "ENGINE_ERROR",
 "error_code": 101, "error_msg": "image load failed: D:/VisionWork/xxx.png",
 "elapsed_ms": 12.0, "defects": []}
```

## 6. teach

Request:
```json
{
  "request_id": "REQ-000200",
  "cmd": "teach",
  "image_path": "D:/VisionWork/teach_20260706_110000.png",
  "recipe_name": "TYPE_A",
  "roi_mode": "AutoFrame",
  "roi_rect": {"left": 0, "top": 0, "right": 0, "bottom": 0},
  "angle_tol_deg": 5.0
}
```

Response:
```json
{
  "request_id": "REQ-000200",
  "cmd": "teach",
  "status": "OK",
  "error_code": 0, "error_msg": "", "elapsed_ms": 1520.0,
  "angle_deg": 1.32,
  "roi_used": {"left": 412, "top": 380, "right": 3422, "bottom": 2368},
  "taught_params": { ... 第 7 節結構 ... },
  "preview": {
    "families": [
      {"axis": "v", "angle_deg": 1.32, "line_count": 24, "pitch_px": 130.4},
      {"axis": "h", "angle_deg": 1.35, "line_count": 18, "pitch_px": 130.1}
    ]
  }
}
```

- LabVIEW 用 JSONtext 把 `taught_params` **子物件原樣抽成字串**存入 Recipe，不解析內容。
- `preview` 供教導畫面目視確認顯示（線數、方向角、間距）。

## 7. taught_params 結構（engine 內部合約，LabVIEW 不解析）

```json
{
  "tp_version": 1,
  "families": [
    {
      "axis": "v",
      "angle_deg": 1.32,
      "pitch_px": 130.4,
      "line_count": 24,
      "positions_px": [412.0, 542.5, 673.1, "... 去旋轉座標系中的線位置 ..."]
    },
    {
      "axis": "h",
      "angle_deg": 1.35,
      "pitch_px": 130.1,
      "line_count": 18,
      "positions_px": [380.0, 510.2, "..."]
    }
  ],
  "thresholds": {
    "cut_bright_thresh": 180,
    "min_break_len_px": 8,
    "band_halfwidth_px": 4
  },
  "reference": {
    "taught_at": "2026-07-06T11:00:00",
    "image": "teach_20260706_110000.png"
  }
}
```

- `thresholds` 目前為預設值；待「已知切穿 vs 已知未切穿」對照影像量化後定案（影像側待辦）。
- schema 演進只動 `tp_version`，LabVIEW 端零改動。

## 8. shutdown

Request:  `{"request_id": "REQ-000999", "cmd": "shutdown"}`
Response: `{"request_id": "REQ-000999", "cmd": "shutdown", "status": "OK", "error_code": 0, "error_msg": "", "elapsed_ms": 0.1}`

回應送出後 server 關閉連線並結束行程。（正常關機仍由主程式管理 server.exe 生命週期；此指令為配合優雅關閉。）

## 9. engine error_code 一覽

| code | 意義 |
|---|---|
| 0 | 無錯誤 |
| 100 | image_path 檔案不存在 |
| 101 | 影像載入失敗（格式壞損） |
| 102 | AutoFrame 找不到大黑框內緣 |
| 103 | 找不到切割線（發現式失敗） |
| 104 | taught_params 缺漏或版本不符 |
| 110 | engine 內部例外（詳見 error_msg 與 log） |
| 120 | JSON 解析失敗（該行不是合法 JSON） |
| 121 | 未知 cmd |
| 122 | 欄位缺漏 / 型別錯誤 / 含非 ASCII |

LabVIEW 端映射：任何非 0 → user error 5402（引擎回報錯誤），error_msg 附帶 engine code。

## 10. Mock 模式

`server.exe --mock` 啟動時：
- `ping` 回 `"mock": true`
- `inspect` 不讀影像，輪流回傳 OK / NG（含 2 個假 defects）/ PLACEMENT_ERROR / DETECTION_ANOMALY（含假 `reason_codes`），供 LabVIEW 端離線開發全部四種路徑
- `teach` 回固定的假 taught_params
