# Sentinel Security Journal

## 2026-07-14 - TCP Protocol Boundary Input Validation for Image Paths
**Vulnerability:** The TCP server endpoint accepted arbitrary `image_path` string inputs for `inspect` and `teach` commands without restricting file extensions or checking for path traversal sequences like `..`.
**Learning:** The server handler passed raw client-supplied paths directly to file loading functions (`engine.py`), assuming LabVIEW client pre-validation. Relying on client-side validation creates a security gap if the TCP socket is accessed directly.
**Prevention:** Validate all file paths at the protocol boundary (`protocol.py`) using strict extension whitelisting (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and rejecting directory traversal (`..`) before routing commands to internal engines or lower-level file I/O operations.
