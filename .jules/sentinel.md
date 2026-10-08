## 2026-07-06 - Image Path Traversal and File Extension Validation in TCP Protocol
**Vulnerability:** The TCP server accepted arbitrary file paths for `image_path` in `inspect` and `teach` commands without validating against directory traversal (`..`) sequences or limiting extensions to supported image formats.
**Learning:** Network endpoints that process file path parameters must enforce path sanitization and extension whitelisting at the protocol parsing boundary before passing file paths to file operations or image loading components.
**Prevention:** Validate `image_path` strictly in `ve_server/protocol.py` by rejecting directory traversal sequences (`..`) and restricting allowed extensions to `.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, and `.tiff`.
