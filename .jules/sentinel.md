## 2026-03-30 - Validate image_path input at TCP protocol boundary
**Vulnerability:** TCP server allowed arbitrary `image_path` parameters in `inspect` and `teach` commands, enabling path traversal attacks (`..`) and processing of arbitrary file types.
**Learning:** The protocol boundary only checked string non-emptiness and ASCII constraints, leaving file system operations in `ve_server/engine.py` exposed to path traversal.
**Prevention:** Strictly validate file extensions against allowed image types (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject directory traversal sequences (`..`) at the protocol parsing layer before processing requests.
