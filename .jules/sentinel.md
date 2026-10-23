# Sentinel's Journal

## 2026-03-30 - Protocol Boundary Input Validation for File Paths
**Vulnerability:** Unvalidated `image_path` inputs in TCP JSON requests (`inspect` and `teach` commands) allowed potential path traversal (`..`) and non-image file processing or retention copying.
**Learning:** In TCP/IPC socket servers processing local file references, input path validation must happen at the protocol boundary (`parse_request`) before reaching lower engine or I/O layers.
**Prevention:** Strictly enforce path sanity checks (reject `..`) and whitelist allowed image file extensions (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) in protocol parsers.
