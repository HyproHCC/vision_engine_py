## 2026-07-16 - TCP Protocol Boundary Input Validation for File Paths
**Vulnerability:** TCP server commands `inspect` and `teach` received unvalidated `image_path` strings, which could contain path traversal sequences (e.g. `..`) or non-image file extensions, leading to path traversal and arbitrary non-image file processing in server file copy handlers.
**Learning:** In socket/TCP RPC architectures where file paths are sent by clients, path validation must occur strictly at the protocol parsing boundary (`ve_server/protocol.py`) before reaching downstream engine file loading or NG copy handlers.
**Prevention:** Enforce strict file extension whitelist (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject `..` path traversal sequences during protocol request parsing.
