# Sentinel Security Journal

## 2026-03-31 - Unsanitized Image Path Traversal and File Extension Restriction in TCP Protocol
**Vulnerability:** The TCP server accepted arbitrary string file paths for `image_path` in `inspect` and `teach` commands without restricting allowed file extensions or filtering path traversal sequences (`..`). This allowed potential arbitrary file reading and directory traversal on the host server.
**Learning:** Incoming protocol string parameters were only checked for ASCII encoding without enforcing strict domain boundary validation for file path structure and extension restrictions.
**Prevention:** Validate file extension against an explicit allowlist (`ALLOWED_IMAGE_EXTS`) and reject directory traversal sequences (`..`) at the protocol parsing boundary (`parse_request`) before handing paths off to engine I/O handlers.
