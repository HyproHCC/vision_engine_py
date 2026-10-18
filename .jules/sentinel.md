# Sentinel Security Journal

## 2026-03-30 - TCP Protocol Image Path Traversal and Extension Validation
**Vulnerability:** Incoming TCP requests for `inspect` and `teach` allowed arbitrary `image_path` strings without extension filtering or directory traversal validation. This could allow attackers or untrusted callers to specify arbitrary system file paths, potentially leading to unauthorized file reading or copying non-image system files to the public `ng/` directory on defects.
**Learning:** System APIs that process file paths passed over network commands must strictly validate path constraints (restricting relative traversal `..`) and enforce strict extension allowlists at the protocol parser boundary before downstream file I/O operations occur.
**Prevention:** Always enforce strict allowlist validation for file extensions and reject path traversal indicators (`..`) at the earliest entry point (`protocol.py`) before attempting file access or file copy operations.
