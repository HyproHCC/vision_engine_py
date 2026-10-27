# Sentinel Security Journal

## 2026-07-16 - Prevent Path Traversal and Non-Image File Access at TCP Boundary
**Vulnerability:** The TCP server endpoint accepted arbitrary `image_path` parameters in `inspect` and `teach` requests without validating directory traversal sequences or file extensions.
**Learning:** Incoming TCP JSON requests at the server boundary could allow arbitrary local file read or file copy operations via `..` path components or unintended file extensions.
**Prevention:** Always sanitize and restrict incoming file path parameters at the protocol boundary (`ve_server/protocol.py`) to safe image extensions (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject directory traversal (`..`) attempts.
