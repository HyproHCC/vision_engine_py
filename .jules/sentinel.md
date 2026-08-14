# Sentinel Security Journal 🛡️

This journal documents critical security learnings and vulnerability preventions for the VisionEngine codebase.

## 2026-07-16 - Path Traversal & Insecure Image Loading in protocol layer
**Vulnerability:** The TCP server commands (`inspect` and `teach`) accepted any arbitrary string as `image_path` without validation. Attackers could specify relative paths containing directory traversal sequences (like `..`) to read arbitrary files, attempt loading non-image files, or cause server crashes.
**Learning:** The boundary logic in `ve_server/protocol.py` only checked if `image_path` was a non-empty string and relied on LabVIEW client validation. Since security should follow the principle of defense in depth and not trust client-side validation alone, validating input at the API/protocol boundary is necessary to prevent severe traversal vulnerabilities.
**Prevention:** Validate all file paths at the protocol boundary. Ensure `image_path` does not contain directory traversal sequences (`..`) and strictly restrict its file extensions to a known-safe whitelist of image formats (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
