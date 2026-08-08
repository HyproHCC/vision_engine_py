# Sentinel Security Journal 🛡️

## 2026-07-16 - [TCP 協定邊界的路徑穿越與任意檔案存取漏洞]
**Vulnerability:** TCP 伺服器的 `inspect` 和 `teach` 指令接受來自用戶端的任意 `image_path` 字串欄位，該路徑未經驗證即直接傳遞給影像載入函數（例如 `cv2.imdecode`、`np.fromfile` 等）。攻擊者可利用路徑穿越序列（如 `..`）讀取、探測或操作系統中的任意非影像檔案，甚至可能將敏感文件複製到公開或 NG 記錄目錄下。
**Learning:** 不能假設用戶端皆為友善或已完成過濾，亦不能僅依賴作業系統的檔案存在檢查。系統邊界處必須對所有外部輸入進行嚴格的格式、長度與範圍驗證（Defense in Depth）。
**Prevention:** 在協定解析邊界（`ve_server/protocol.py`）強制執行兩道安全檢查：1. 將路徑分割並徹底拒絕包含 `..` 的路徑片段，防範路徑穿越；2. 提取副檔名並限制僅允許常見影像格式（如 `.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`），避免讀取任意類型的敏感檔案。
