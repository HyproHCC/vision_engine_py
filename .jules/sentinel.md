## 2026-08-16 - TCP Protocol Boundary Image Path Sanitization
**Vulnerability:** TCP server `inspect` and `teach` commands accepted arbitrary string paths for `image_path` without directory traversal checks (`..`) or file extension validation, allowing potential path traversal and processing of unauthorized non-image file types.
**Learning:** ASCII character validation alone is insufficient for file path parameters passed over TCP protocols.
**Prevention:** Always validate against directory traversal sequences (`..`) and enforce a strictly defined file extension whitelist (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) at the protocol parsing layer (`ve_server/protocol.py`) before passing paths to file I/O operations.
