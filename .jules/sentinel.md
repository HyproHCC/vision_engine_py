# Sentinel 🛡️ 安全日誌

## 2026-03-24 - 協定邊界之路徑周遊與非預期副檔名安全漏洞防護
**Vulnerability:** 協定邊界解析（`ve_server/protocol.py`）未對傳入的 `image_path` 進行路徑周遊防護（未檢查 `..` 序列）與影像副檔名限制，使得潛在的惡意 Client 可藉此傳入任意路徑或非影像檔案。
**Learning:** 原系統預設來自內部的 LabVIEW Client 請求皆為安全且可信任，因此未在第一時間於協定解析邊界（Protocol boundary）強制過濾不合規或具威脅性的路徑字串。
**Prevention:** 於 `ve_server/protocol.py` 嚴格限制 `image_path` 不得包含 `..` 遍歷序列，且副檔名必須僅限於 `.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`，不符則回傳統一的協定格式錯誤代碼。
