# Sentinel's Journal

🛡️ Security is a core design principle. This journal tracks critical security learnings in VisionEngine.

## 2026-07-16 - [無限制之影像路徑附檔名導致任意檔案讀取與複製漏洞]
**Vulnerability:** 伺服器端之 `inspect` 與 `teach` 指令接受任意 `image_path` 參數，且未對其進行附檔名或檔案類型驗證。若傳入非影像之系統敏感檔案（例如系統設定檔或密鑰檔案），在檢測到斷點時，伺服器會盲目地複製並保存該檔案到 NG 目錄中，造成任意檔案讀取與複製風險 (Arbitrary File Read / Path Traversal)。
**Learning:** 原因在於 API 協定邊界 (`ve_server/protocol.py`) 僅對欄位是否為非空字串及是否符合 ASCII 進行了基本驗證，而忽略了對檔案類型與副檔名的嚴格限制，使得後續的檔案 I/O 操作直接暴露於潛在的惡意輸入之下。
**Prevention:** 在協定邊界對輸入的 `image_path` 進行副檔名白名單驗證（僅允許常見的影像格式如 `.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`），從根本上杜絕非影像格式之任意檔案讀取與處理操作，實現深度防禦 (Defense in Depth)。
