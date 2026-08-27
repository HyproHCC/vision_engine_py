## 2026-07-16 - Protocol Boundary Input Validation & Path Traversal Prevention
**Vulnerability:** The TCP server protocol parser (`ve_server/protocol.py`) accepted any string for `image_path` without checking for path traversal sequences (`..`) or image file extension validity.
**Learning:** External requests sent over TCP socket directly reached file system calls without strict validation at the server boundary, risking arbitrary file read or unintended file operations.
**Prevention:** Always perform strict input validation, enforce explicit extension white-lists (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`), and reject relative path traversal tokens (`..`) at the edge of protocol parsing before passing parameters to core engine logic.
