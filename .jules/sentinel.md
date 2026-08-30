## 2026-03-29 - Protocol Boundary File Path Validation & Traversal Prevention
**Vulnerability:** The TCP server accepted `image_path` in `inspect` and `teach` commands without validating directory traversal sequences (`..`) or restricting file extensions, which could allow path traversal or arbitrary file operations on non-image files.
**Learning:** Incoming request JSON fields were passed to filesystem loading and NG copy operations without path sanitization at the protocol parsing layer.
**Prevention:** Strictly enforce image file extension allowlists (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject path traversal sequences (`..`) at the protocol boundary (`ve_server/protocol.py`).
