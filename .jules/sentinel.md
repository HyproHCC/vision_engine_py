# Sentinel Journal

## 2026-03-30 - Protocol Boundary Path Traversal and Extension Validation
**Vulnerability:** TCP protocol endpoint accepted unchecked `image_path` strings in `inspect` and `teach` commands, allowing directory traversal sequences (e.g. `..`) and arbitrary file extensions.
**Learning:** File path parameters coming over TCP JSON API need strict validation at the protocol boundary prior to filesystem or engine operations.
**Prevention:** Validate file extension whitelist (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject relative directory traversal sequences (`..`) in `parse_request()`.
