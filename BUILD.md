# server.exe 打包與部署說明

## 環境
- Windows 上以 **Python 3.11+ (64-bit)** 打包即可（engine 是獨立行程，
  不受 LabVIEW 32-bit 限制；TCP 之間無位元數相依）
- `pip install -r requirements.txt pyinstaller`

## 打包
```bat
pyinstaller --onefile --name ve_server ^
  --hidden-import cv2 ^
  ve_server\main.py
```
產出 `dist\ve_server.exe`。

## 部署佈局（與主程式管理的工作資料夾配合）
```
D:\VisionEngine\
  ve_server.exe
  config.json          （複製 config.default.json 修改；缺漏欄位用內建預設）
  logs\                （自動建立，rotating logs）
  ng\                  （NG 留存，依 ng_retention_days 自動清理）
```

## 啟動參數
```
ve_server.exe                 正常模式
ve_server.exe --mock          mock 模式（LabVIEW 離線開發）
ve_server.exe --port 5711     指定埠
```

## 重新產生 server.exe 後必驗項目（歷史教訓）
1. **行尾必須是 `\r\n`**：用 `test_client.py ping` 收包確認（LabVIEW TCP Read
   CRLF 模式在只有 `\n` 時會靜默失敗）。本專案由 `protocol.encode_response`
   統一處理，但重打包後仍要實測一次。
2. mock 模式三種 verdict（OK/NG/PLACEMENT_ERROR）輪替正常
3. `shutdown` 指令後行程確實結束（工作管理員確認無殘留）

## 快速自我測試
```bat
ve_server.exe --mock
python test_client.py demo      （另一個視窗）
python test_client.py shutdown
```

## 待對照影像後要調的參數
`config.json` 的 `algo` 區（或教導後存於配方 taught_params.thresholds）：
- `cut_bright_thresh`（目前 180）：切穿/未切穿的亮度分界
- `min_break_len_px`（目前 8）：最短回報斷點長度
- `gap_merge_px`（目前 6）：被交叉線切開的暗段縫合距離
- `edge_guard_px`（目前 10）：線末端忽略帶

「暗段 = 未切穿 vs 被晶粒遮擋」的區分邏輯若確認需要，
加在 `ve_core/breaks.py`（介面不變；演算法一律進 ve_core，見 ARCHITECTURE.md 2.2）。
