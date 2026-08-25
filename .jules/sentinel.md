## 2026-07-16 - Path Traversal and File Extension Validation in Server Protocol
**Vulnerability:** Unsanitized `image_path` in incoming TCP protocol requests could allow path traversal sequences (`..`) and arbitrary file extension inputs.
**Learning:** `ve_server/protocol.py` parsed `image_path` without checking for path traversal or restricting allowed file extensions, relying solely on downstream file loading.
**Prevention:** Validate file paths at the protocol boundary in `parse_request` by enforcing allowed image extensions (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and rejecting directory traversal sequences (`..`).
