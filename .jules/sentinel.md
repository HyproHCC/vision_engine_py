## 2026-03-31 - [Protocol Boundary Input Validation for Image Paths]
**Vulnerability:** Unsanitized `image_path` inputs in TCP protocol layer allowed potential directory traversal sequences and non-image file path execution.
**Learning:** Adding validation at the protocol parser level (`ve_server/protocol.py`) prevents invalid file formats and directory traversal attempts before engine processing or file system access.
**Prevention:** Always enforce strict file extension whitelists and path structure validation at protocol endpoints before handling path strings.
