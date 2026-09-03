# Sentinel Security Journal

## 2026-03-31 - Path Traversal & Non-Image Execution Prevention at TCP Protocol Boundary
**Vulnerability:** Incoming TCP protocol requests (`inspect` and `teach`) accepted arbitrary file paths for `image_path` without checking for path traversal (`..`) or restricting allowed image extensions, allowing potential arbitrary file read / processing.
**Learning:** In socket-based JSON RPC protocols without web frameworks, input validation must be explicitly performed at the request parsing layer (`ve_server/protocol.py`) before passing parameters down to file system or image decoding operations (`ve_server/engine.py`).
**Prevention:** Always validate file extension whitelists (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and enforce directory traversal checks (`..`) at the protocol parsing boundary, returning a standard error code (`E_BAD_FIELD`).
