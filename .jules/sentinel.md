# Sentinel Journal

## 2026-10-17 - Protocol Boundary Image Path Traversal & File Extension Validation
**Vulnerability:** The TCP server protocol layer (`ve_server/protocol.py`) accepted any non-empty string as `image_path` for `inspect` and `teach` commands, allowing potential directory traversal sequences (`..`) and reading of arbitrary non-image files via underlying image loading and NG file copying logic.
**Learning:** In industrial PC / LabVIEW client integrations, TCP server endpoints often assume clients are trustworthy or on local loopback, leaving path inputs unvalidated at protocol entry points. When filenames or paths are passed to filesystem APIs (`cv2.imdecode`, file read/write copies for NG retention), unchecked inputs can escape intended directories or process unintended files.
**Prevention:** Validate input strings strictly at the protocol boundary before dispatching to backend engines. Restrict file extensions to an explicit whitelist of image formats (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject relative path traversal patterns (`..`).
