## 2026-07-16 - TCP Protocol Boundary Input Validation for File Paths
**Vulnerability:** Unsanitized `image_path` in TCP `inspect` and `teach` commands allowed path traversal sequences (`..`) and non-image extensions, potentially leading to arbitrary file access or unintended file reading/copying.
**Learning:** In TCP protocol dispatching without web frameworks, file path inputs directly control file system calls (`np.fromfile`, `open`).
**Prevention:** Strictly validate file extensions against an explicit allowlist (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) and reject directory traversal sequences (`..`) at the protocol parsing boundary prior to disk operations.
