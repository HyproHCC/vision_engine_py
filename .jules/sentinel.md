## 2026-03-30 - Path Traversal & File Extension Validation at Protocol Boundary
**Vulnerability:** The TCP server accepted arbitrary file paths in `image_path` without checking for directory traversal (`..`) or restricting file extensions, allowing potential unauthorized file access or decoder crash attacks.
**Learning:** In a socket server receiving JSON IPC commands, string path inputs must be validated at the boundary before calling file loading or decoder APIs (`np.fromfile` / `cv2.imdecode`).
**Prevention:** Strictly reject path traversal tokens (`..`) and enforce an allowlist of permitted image file extensions (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) in `parse_request`.
