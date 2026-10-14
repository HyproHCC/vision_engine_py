# Sentinel's Security Journal

## 2026-07-16 - Path Traversal and Non-Image Extension Validation in Protocol Parser
**Vulnerability:** The TCP server protocol parser (`ve_server/protocol.py`) accepted arbitrary file paths in the `image_path` field for `inspect` and `teach` commands without validating file extensions or checking for path traversal sequences like `..`.
**Learning:** While higher-level image loaders checking file existence before reading, validating inputs at the network protocol boundary prevents directory traversal attacks and restricts processing to valid image formats (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
**Prevention:** Always sanitize and validate file path parameters at the protocol boundary prior to passing them down to internal subsystems.
