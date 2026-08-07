## 2026-07-14 - [防範 TCP 協定層路徑穿越與任意非圖片檔案讀取漏洞]
**Vulnerability:** 在 TCP 協定層的指令 `inspect` 與 `teach` 中，傳入的 `image_path` 未進行任何字串安全性過濾。攻擊者可藉由路徑穿越字元序列 `..`（例如 `../../secret.txt`）存取限制區域外的任意檔案。此外，系統未對檔案副檔名進行白名單驗證，導致可能載入非圖片格式的敏感檔案，增加阻斷服務（DoS）或敏感資訊洩漏的風險。
**Learning:** 演算法核心（`ve_core`）為無 I/O 的純演算法，雖然不直接處理 I/O 驗證，但 TCP 協定轉接層（`ve_server/protocol.py`與`ve_server/engine.py`）作為外部輸入的邊界，卻未對外部傳入的路徑字串進行充分防禦。
**Prevention:** 在協定解析的最前端（`ve_server/protocol.py` 中的 `parse_request`）建立強固的邊界檢查：主動拒絕任何包含 `..` 的路徑，並僅允許白名單副檔名（`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`，不區分大小寫），防範於未然。
