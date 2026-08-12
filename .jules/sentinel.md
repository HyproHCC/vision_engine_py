## 2026-03-01 - [Protocol Layer Input Validation]
**Vulnerability:** Arbitrary non-image files or directory traversal attempts could be specified in the `image_path` parameter of TCP server requests, potentially leading to unauthorized system actions or resource exposure if unchecked by the underlying image loader.
**Learning:** Checking file extensions and preventing directory traversal (e.g. searching for ".." segments in path components) at the TCP protocol parsing boundary (`ve_server/protocol.py`) provides a robust defense-in-depth layer before the application attempts any backend file operations.
**Prevention:** Always strictly validate and sanitize file path inputs at the boundary of external-facing interfaces before passing them to internal subsystems.
