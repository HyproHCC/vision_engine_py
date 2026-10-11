## 2026-10-11 - Image Path Validation at Protocol Boundary
**Vulnerability:** TCP server endpoints accepted `image_path` string inputs without validating path traversal sequences (`..`) or limiting file extensions.
**Learning:** In TCP protocol boundaries where file paths are accepted from clients, input validation must enforce strict extension checks and block directory traversal characters before downstream image IO modules process the path.
**Prevention:** Always validate and sanitize string fields at `ve_server/protocol.py` before passing request objects to dispatcher or engine handlers.
