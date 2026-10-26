# Sentinel Journal - Critical Learnings

## 2026-10-26 - TCP Protocol Boundary Path Traversal and File Extension Validation
**Vulnerability:** Unvalidated `image_path` in TCP JSON requests (`inspect` and `teach` commands) could allow arbitrary file path inputs, including path traversal sequences (`..`) and non-image files, exposing the system to unexpected file read operations or potential directory traversal risks.
**Learning:** In a local TCP protocol serving automated vision clients (e.g. LabVIEW), client inputs must still be validated strictly at the server protocol boundary before being passed to underlying image loaders (`np.fromfile` or OpenCV).
**Prevention:** Enforce strict checks on `image_path` at `parse_request`: reject relative path traversal sequences (`..`) and restrict extensions to supported image formats (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
