## 2026-07-28 - [Security Vulnerability: Directory Traversal and Arbitrary File Access via image_path in ve_server]
**Vulnerability:** The `image_path` parameter in `inspect` and `teach` commands in `ve_server/protocol.py` lacked proper input validation, exposing the server to directory traversal (e.g., using `..` sequences) and arbitrary file format operations.
**Learning:** Untrusted boundary inputs from clients, even if validated on the client side (e.g., LabVIEW), must always be validated strictly at the server protocol boundary for defense in depth.
**Prevention:** Validate input parameters at the API/protocol layer. Reject any path traversal sequences (such as `..`) and restrict path extensions to a strict whitelist (e.g., specific image formats).
