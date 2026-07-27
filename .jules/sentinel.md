# Sentinel Security Journal

## 2026-03-05 - Missing Input Path Validation and Extension Restriction in TCP API
**Vulnerability:** The TCP server commands (`inspect` and `teach`) accepted any `image_path` string without validating for path traversal sequences (`..`) or checking if the file extension is a valid image format. This could lead to path traversal vulnerabilities and unauthorized operations on non-image files if the server runs in a highly privileged context or processes user-influenced files.
**Learning:** The application trusted the client-side validation (LabVIEW) for inputs, violating the principle of "Trust nothing, verify everything." Input validation must always be performed at the server's protocol parsing boundary (defense in depth).
**Prevention:** Strictly validate `image_path` at the protocol boundary by rejecting directory traversal sequences (e.g., `..`) and enforcing a strict case-insensitive file extension allowlist (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
