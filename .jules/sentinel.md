# Sentinel Journal - Critical Security Learnings

## 2026-03-30 - TCP Protocol Image Path Traversal and File Extension Validation
**Vulnerability:** The TCP protocol boundary (`ve_server/protocol.py`) accepted arbitrary `image_path` string inputs without verifying file extensions or directory traversal sequences (`..`).
**Learning:** Downstream engine processing (`load_gray` and `_save_ng_copy`) performs file reading and copies defect images to the NG retention directory (`ng_dir`). Without protocol boundary validation, unvalidated inputs could allow directory traversal or processing non-image files.
**Prevention:** Strictly validate `image_path` at the `ve_server/protocol.py` entry point by rejecting paths containing `..` and restricting extensions to allowed image types (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
