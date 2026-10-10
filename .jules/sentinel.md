## 2026-07-16 - Path Traversal and Arbitrary File Extension Validation in Protocol Endpoint

**Vulnerability:** The TCP server endpoint accepted arbitrary string file paths in `image_path` for `inspect` and `teach` commands without restricting extensions or checking for directory traversal sequences (e.g. `..`), which could allow unauthorized reading of non-image or sensitive system files via server error messages or file copy operations.
**Learning:** Checking string ASCII status alone is insufficient to guarantee path safety when dealing with file operations across protocol boundaries.
**Prevention:** Validate file extensions against an explicit whitelist (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and enforce directory traversal checks (`..`) strictly at the request parsing layer (`ve_server/protocol.py`).
