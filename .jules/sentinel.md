# Sentinel Security Journal

## 2026-07-16 - Path Traversal and File Extension Validation in TCP Protocol
**Vulnerability:** Incoming TCP protocol requests (`inspect`, `teach`) accepted arbitrary `image_path` strings without validating path traversal sequences (`..`) or restricting file extensions to supported image types (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
**Learning:** Even when input paths are expected to be checked by client components (e.g. LabVIEW GUI), server protocol handlers must strictly enforce input validation at the boundary before passing paths to file system operations like `load_gray` or `_save_ng_copy`.
**Prevention:** Validate both file extensions against an explicit allowlist and disallow directory traversal components (`..`) in all protocol handlers accepting file paths.
