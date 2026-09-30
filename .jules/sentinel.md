# Sentinel's Journal - Security Learnings

## 2026-03-30 - TCP Protocol Boundary Path Traversal and File Extension Validation
**Vulnerability:** The TCP server accepted arbitrary `image_path` string inputs for `inspect` and `teach` commands without restricting file extensions or checking for path traversal (`..`), allowing clients to trigger image loading and file operations on arbitrary system files.
**Learning:** Parsing user-supplied file paths in command handlers without strict boundary validation creates risk of unauthorized file reads or unexpected file copying during error/NG logging.
**Prevention:** Always sanitize and validate file paths at the protocol boundary in `ve_server/protocol.py` by enforcing strict extension whitelist (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and rejecting directory traversal sequences (`..`).
