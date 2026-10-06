# Sentinel's Journal

## 2026-03-30 - Protocol Boundary Image Path Validation
**Vulnerability:** TCP server `inspect` and `teach` protocol handlers accepted arbitrary `image_path` string inputs without validating path traversal sequences (`..`) or restricting file extensions.
**Learning:** `ve_server/protocol.py` validates protocol JSON structure and fields, but lacked input sanitization on file paths, allowing potential directory traversal or arbitrary non-image file processing by backend image loaders.
**Prevention:** Enforce strict path traversal rejection (`..`) and explicit image file extension checks (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) at the protocol parsing stage in `ve_server/protocol.py`.
