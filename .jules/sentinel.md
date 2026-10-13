## 2026-03-30 - Path Traversal & Extension Validation at Protocol Boundary

**Vulnerability:** The TCP server protocol parser in `ve_server/protocol.py` accepted any string as `image_path` for `inspect` and `teach` commands without validating file extension or checking for directory traversal sequences (such as `..`). This could allow attackers or faulty clients to cause directory traversal or arbitrary non-image file operations.

**Learning:** Application protocols handling file system paths must perform input validation and sanitization at the network protocol boundary before passing paths down to backend file operations (`load_gray` / file reading).

**Prevention:** Always restrict accepted file extensions to an explicit whitelist (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and explicitly reject path traversal sequences (such as `..`) at the protocol parsing layer.
