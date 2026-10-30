## 2026-03-30 - Path Traversal and File Extension Validation at TCP Boundary
**Vulnerability:** Unvalidated image paths passed over TCP requests (`inspect` / `teach`) allowed potential directory traversal sequences (`..`) and non-image extensions.
**Learning:** Checking string fields strictly for allowed file extensions and blocking relative path components at protocol parsing boundary prevents unauthenticated arbitrary file operations or unintended path traversal in downstream engine processing.
**Prevention:** Perform early strict whitelist validation on file extensions and check for directory traversal markers in input handling functions.
