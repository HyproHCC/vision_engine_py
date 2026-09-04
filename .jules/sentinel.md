## 2026-03-31 - Protocol Boundary Image Path Traversal Prevention
**Vulnerability:** TCP protocol parser (`ve_server/protocol.py`) accepted any non-empty string as `image_path` for `inspect` and `teach` commands, allowing path traversal (`..`) sequences and non-image extensions.
**Learning:** Incoming requests at protocol boundaries must validate string fields against both directory traversal patterns and strict file extension whitelist before passing file paths to system calls or OpenCV file decoders.
**Prevention:** Validate `image_path` at `parse_request` by disallowing `..` path components and restricting extensions to allowed image formats (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
