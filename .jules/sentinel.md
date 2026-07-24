# Sentinel Security Journal

## 2025-02-15 - [在協定邊界實施路徑穿越防護與影像副檔名白名單限制]
**Vulnerability:** TCP 伺服器在解析 `inspect` 與 `teach` 指令時，直接接受並載入了來自客戶端傳送的任意 `image_path` 字串。這導致潛在的目錄穿越風險（例如：藉由包含 `..` 的路徑讀取非預期目錄中的檔案）與讀取任意非影像格式檔案的安全隱憂。
**Learning:** 在工業通訊（如 LabVIEW 與 Python 之間的 TCP Socket 串接）中，即使客戶端已有基本防禦，伺服器端的協定解析邊界（protocol boundary）仍必須嚴格把關。未經校驗的檔案路徑輸入會暴露出系統底層檔案讀取的攻擊面。
**Prevention:** 在 `ve_server/protocol.py` 協定解析層阻斷含有目錄穿越特徵 `..` 的請求，並嚴格限縮 `image_path` 的副檔名至安全的名單中（`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`），從根本上實踐「不信任、必校驗」的縱深防禦（Defense in Depth）安全策略。
