## 2026-03-31 - Protocol Boundary Path Traversal and Extension Check
**Vulnerability:** TCP protocol commands (`inspect`, `teach`) accepted arbitrary file paths for `image_path` without checking for path traversal sequences (`..`) or restricting file extensions to expected image types.
**Learning:** Downstream engine image loading (`load_gray`) and NG image retention copy (`_save_ng_copy`) performed I/O on raw string parameters directly received from TCP requests.
**Prevention:** Validate string path parameters at the protocol parsing boundary (`ve_server/protocol.py`) before handing them over to business logic or file system operations.
