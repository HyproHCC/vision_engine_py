# Sentinel Security Journal 🛡️

## 2025-03-01 - [Path Traversal and Arbitrary File Access in TCP Protocol Boundary]
**Vulnerability:** The TCP server commands (`inspect` and `teach`) accepted an arbitrary `image_path` string field from clients, which was passed directly to file loading functions (`np.fromfile` and standard `open`) without path validation. An attacker could specify directory traversal sequences (e.g., `..`) and arbitrary file paths, potentially leading to unauthorized file loading (which could crash the server or expose contents via errors/logging) and duplicating arbitrary files into the public/NG logging directory.
**Learning:** Checking for file existence or assuming correct clients is insufficient. Input boundaries must always sanitize and strictly validate all file path inputs.
**Prevention:** Enforce strict validation at the protocol boundary (`ve_server/protocol.py`): restrict allowed file extensions to image files (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject any path traversal segments (`..`).
