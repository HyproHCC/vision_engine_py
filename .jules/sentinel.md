# Sentinel Security Journal

## 2026-07-15 - TCP Protocol Boundary Path Traversal and Extension Validation
**Vulnerability:** The TCP server endpoint `ve_server/protocol.py` accepted any string for `image_path` in `inspect` and `teach` commands without checking for directory traversal (`..`) or constraining file extensions. An attacker could specify non-image file paths or directory traversal paths, causing arbitrary file reads or copying sensitive non-image files into the NG directory.
**Learning:** Protocol boundaries must validate all file path inputs before handing them off to lower layers or file system handlers.
**Prevention:** Strictly enforce path traversal checks (`..`) and file extension whitelist validation at the protocol parsing boundary (`ve_server/protocol.py`) before attempting image decoding or file operations.
