## 2026-03-04 - 影像路徑遍歷與不安全副檔名漏洞驗證阻擋
**Vulnerability:** 伺服器端（`ve_server`）在處理 `inspect` 與 `teach` 指令時，雖限制了 `image_path` 欄位為 ASCII，但未對其內容進行路徑偏訪（directory traversal, `..`）與檔案副檔名過濾，可能導致惡意使用者讀取任意檔案或載入非影像格式之惡意檔案。
**Learning:** 協定解析層（`ve_server/protocol.py`）只實作了型態與基本 ASCII 驗證，忽略了高風險的外部輸入檔案路徑驗證。
**Prevention:** 於協定邊界對 `image_path` 強制檢查是否包含 `..` 偏訪序列，並嚴格限制副檔名僅能為合法影像格式（如 `.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`）。
