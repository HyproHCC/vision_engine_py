## 2026-03-29 - Input Validation for File Paths at Protocol Boundary
**Vulnerability:** Unsanitized `image_path` parameters in `inspect` and `teach` protocol commands allowed potential directory traversal (`..`) and loading/copying of arbitrary non-image files.
**Learning:** The protocol layer validated string ASCII constraints and ROI parameters but omitted path sanitization before passing paths to file system calls (`load_gray` and `_save_ng_copy`).
**Prevention:** Validate all file paths at the protocol entry point (`ve_server/protocol.py`), rejecting `..` traversal sequences and enforcing an explicit whitelist of allowed image extensions (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
