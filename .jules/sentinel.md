## 2026-03-08 - Path Traversal and File Extension Validation in Protocol Boundary
**Vulnerability:** TCP server accepted arbitrary file paths in `image_path` for `inspect` and `teach` commands without path traversal checks or extension restrictions.
**Learning:** In TCP protocol endpoints receiving local file paths for processing (like OpenCV `imdecode`), unvalidated input paths allow path traversal (`..`) and arbitrary file access probing.
**Prevention:** Validate file extension against an explicit allowlist (.png, .bmp, .jpg, .jpeg, .tif, .tiff) and reject directory traversal (`..`) at the protocol parser layer (`ve_server/protocol.py`).
