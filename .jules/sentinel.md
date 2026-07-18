# Sentinel Security Journal

## 2026-03-05 - [TCP server image_path path traversal and arbitrary file check/read vulnerability]
**Vulnerability:** The TCP server accepts arbitrary string as `image_path` and performs `os.path.isfile()` and `np.fromfile()` on it without checking the file extension or path structure. This can lead to Local File Inclusion / Path Traversal or Oracle attacks where an attacker can check if sensitive files (e.g., config files, system files) exist or trigger decoding of non-image files.
**Learning:** The TCP interface was designed for a trusted local LabVIEW client but runs a socket server which is exposed. Input validation at the protocol boundary (strict whitelist of allowed file extensions) is essential for security.
**Prevention:** Restrict `image_path` to only allowed image extensions (`.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`) at the `ve_server/protocol.py` level to reject any arbitrary non-image path accesses before any filesystem operation takes place.
