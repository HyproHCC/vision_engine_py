# Sentinel Security Journal

## 2025-02-18 - TCP Protocol Boundary Path Traversal and Extension Validation
**Vulnerability:** In `ve_server/protocol.py`, `image_path` supplied in `inspect` and `teach` TCP commands was checked for ASCII compliance but lacked validation against path traversal sequences (`..`) and non-image file extensions.
**Learning:** Accepting untrusted file paths at the protocol layer allows potential path traversal or unexpected file handling downstream in file read/copy routines (such as NG image archiving).
**Prevention:** Always validate file path inputs at the network/protocol boundary by explicitly checking for path traversal sequences and constraining file extensions to an allowed whitelist.
