## 2026-07-16 - TCP Protocol Boundary Path Traversal & File Extension Validation
**Vulnerability:** Unsanitized `image_path` input in TCP protocol requests (`inspect` and `teach`) allowed arbitrary file paths, including directory traversal sequences (`..`) and non-image extensions.
**Learning:** In a TCP JSON server handling file system parameters, validating data types alone is insufficient. Without explicit path traversal checks and strict file extension whitelisting at the protocol parsing boundary, attackers could trigger read/copy operations on arbitrary files on the server.
**Prevention:** Strictly validate `image_path` against `ALLOWED_IMAGE_EXTS` (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and block any paths containing `..` in `ve_server/protocol.py`.
