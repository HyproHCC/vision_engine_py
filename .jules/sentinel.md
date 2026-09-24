# Sentinel's Journal - Critical Security Learnings

## 2026-09-24 - TCP Protocol Boundary Image Path Sanitization & Extension Validation
**Vulnerability:** Unsanitized `image_path` string inputs accepted via TCP JSON commands (`inspect`, `teach`) could allow directory traversal sequence (`..`) and non-image file processing operations.
**Learning:** External client parameters passed directly into file opening utilities (such as `np.fromfile` or file copy operations for NG retention) must be validated strictly at the protocol entry point (`parse_request`).
**Prevention:** Strictly enforce path traversal restrictions (disallow `..`) and restrict file extensions to known image types (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) at the protocol parsing boundary before passing file paths down to engine/file layers.
