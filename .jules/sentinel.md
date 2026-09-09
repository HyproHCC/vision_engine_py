## 2026-09-09 - TCP Protocol Image Path Input Validation & Traversal Prevention
**Vulnerability:** Unchecked `image_path` in `inspect` and `teach` commands accepted arbitrary file paths with non-image extensions and directory traversal sequences (`..`), potentially allowing arbitrary file access and unwanted disk/IO operations.
**Learning:** Input validation must occur strictly at the protocol boundary (`ve_server/protocol.py`) before request dispatch or engine consumption.
**Prevention:** Enforce directory traversal checks (`..`) and strict file extension whitelist validation (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) in protocol parsing.
