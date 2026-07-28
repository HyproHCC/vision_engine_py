## 2026-07-28 - [安全性漏洞：ve_server 中藉由 image_path 進行的路徑追溯與任意檔案存取]
**Vulnerability:** 在 `ve_server/protocol.py` 中，針對 `inspect` 與 `teach` 指令的 `image_path` 欄位缺乏輸入驗證，使伺服器面臨目錄走訪/路徑追溯（Directory Traversal，例如 `..`）及處理任意檔案格式的風險。
**Learning:** 來自客戶端的邊界輸入，即使已在客戶端（如 LabVIEW）進行了驗證，也必須在伺服器的協定邊界進行嚴格驗證（縱深防禦，Defense in Depth）。
**Prevention:** 務必在 API 或協定層級驗證參數。檢查路徑追溯字串（例如 `..`）並將參數限制在特定的白名單允許值（例如特定的副檔名）。
