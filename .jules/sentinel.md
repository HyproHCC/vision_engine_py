## 2026-07-14 - TCP Protocol Boundary Path Traversal and Non-Image Extension Risk
**Vulnerability:** The TCP server accepted `image_path` in `inspect` and `teach` commands without validating path traversal sequences (`..`) or enforcing image file extension restrictions.
**Learning:** The server processes client requests at a low boundary (TCP JSON interface) where path inputs were directly passed to file system operations like `np.fromfile()` and `open()`.
**Prevention:** Always validate `image_path` fields at the protocol parsing boundary (`ve_server/protocol.py`) against allowed image extensions (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject any path containing directory traversal sequences (`..`).
