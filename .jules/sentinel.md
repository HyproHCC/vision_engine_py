## 2026-03-30 - Protocol Image Path Traversal and Extension Validation
**Vulnerability:** TCP server allowed arbitrary string paths for `image_path` without checking file extensions or directory traversal sequences (`..`).
**Learning:** Incoming protocol fields used in file I/O operations must be validated at the protocol boundary (`parse_request`) before reaching backend engine operations.
**Prevention:** Enforce whitelist checking for valid image extensions (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject any path containing `..` to prevent directory traversal and arbitrary file reads.
