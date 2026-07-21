# Sentinel Security Journal

## 2026-07-06 - Image Path Directory Traversal and Arbitrary File Access Validation
**Vulnerability:** The TCP server endpoint accepted arbitrary string file paths via the `image_path` field for `inspect` and `teach` commands without validating the extension or location, which could allow path traversal or arbitrary non-image file operations (e.g. attempting to read system files or arbitrary files via CPU/OpenCV decoders).
**Learning:** The lack of protocol-boundary input validation for the `image_path` parameter allowed any file path to be passed down to the lower level parser and image decoders. Adding extension checks restricts the attack surface and prevents scanning or processing unauthorized file types.
**Prevention:** Always validate user-controlled file path parameters at the earliest protocol boundaries. Limit allowed file extensions to only those explicitly required by the business logic (e.g., standard image formats like `.png`, `.bmp`, `.jpg`, `.jpeg`, `.tif`, `.tiff`).
