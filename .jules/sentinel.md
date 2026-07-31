# Sentinel Security Journal 🛡️

## 2026-07-30 - Prevent Path Traversal and Non-Image File Read in TCP Server Protocol
**Vulnerability:** The TCP server protocol layer (`ve_server/protocol.py`) accepted any string value for `image_path` under `inspect` and `teach` commands without validation. Since the engine downstream loaded the image directly using `np.fromfile(image_path)` and decoded it with `cv2.imdecode`, a malicious client could specify arbitrary files on the filesystem (e.g. `../../etc/passwd` or sensitive system files). While OpenCV would fail to decode non-image files, attempting to read them using `np.fromfile` could lead to sensitive file access, memory usage issues, and directory traversal vulnerability exploitation.

**Learning:** When developing local or network API wrappers around OS and filesystem functions (such as reading files via `np.fromfile`), the boundary layer (the protocol parser) must validate inputs defensively even if there are internal checks downstream. Assuming the downstream component (OpenCV) will safely discard non-image files bypasses the "defense in depth" principle and exposes the file read system to directory traversal.

**Prevention:**
1. Always validate incoming filesystem paths at the API/protocol boundary.
2. Explicitly reject path traversal sequence patterns (such as `..`, `../`, `..\\`) to ensure requests stay within safe bounds.
3. Restrict incoming file paths to a strict whitelist of expected/allowed file extensions (e.g., `.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
