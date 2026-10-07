## 2026-03-31 - Path Traversal and Unrestricted File Reading via TCP Protocol Boundary
**Vulnerability:** `inspect` and `teach` commands accepted `image_path` parameters without verifying file extensions or directory traversal sequences (`..`), allowing arbitrary file reading on the server via `load_gray()` or `_save_ng_copy()`.
**Learning:** Protocol request parsers validated ASCII character constraints and required field existence but lacked validation for path traversal sequences and allowed file format whitelisting.
**Prevention:** Always enforce path traversal checks (`".." in path`) and strictly restrict file extensions against an allowed list at the protocol boundary before performing any file I/O operations.
