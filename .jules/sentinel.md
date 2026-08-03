# Sentinel Security Journal

## 2026-07-16 - Path Traversal & Extension Validation at Protocol Boundary
**Vulnerability:** Incoming TCP commands (`inspect` and `teach`) accept an arbitrary `image_path` string without validation. If an attacker exploits this, they can perform path traversal to read or disclose sensitive system files (e.g. if a defect is found, the backend copies the arbitrary target file to the NG folder, making it accessible).
**Learning:** The protocol layer trusted the `image_path` parameter entirely because of the assumption that LabVIEW client had already sanitized it. This lacks a "defense-in-depth" posture where the backend must always distrust and validate incoming parameters.
**Prevention:** Always validate parameters at the protocol parsing boundary. Restrict paths from using path traversal sequences (e.g. `..`) and enforce a strict allowlist of file extensions (e.g. `.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) before processing any file I/O operations.
