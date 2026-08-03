# -*- coding: utf-8 -*-
import pytest
from ve_server import protocol as P

def test_parse_request_valid_image_paths():
    # Valid paths and extensions
    valid_paths = [
        "image.png",
        "folder/image.bmp",
        "C:\\path\\to\\image.jpg",
        "/var/tmp/image.jpeg",
        "img.tif",
        "img.tiff",
        "IMG.PNG"  # Case insensitivity
    ]
    for path in valid_paths:
        req = {
            "request_id": "REQ-123",
            "cmd": "inspect",
            "image_path": path
        }
        parsed = P.parse_request(P.json.dumps(req))
        assert parsed["image_path"] == path

def test_parse_request_path_traversal_rejected():
    # Invalid paths containing directory traversal
    invalid_paths = [
        "../image.png",
        "folder/../../image.png",
        "..\\image.png",
        "folder\\..\\image.bmp",
    ]
    for path in invalid_paths:
        req = {
            "request_id": "REQ-123",
            "cmd": "inspect",
            "image_path": path
        }
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(P.json.dumps(req))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg

def test_parse_request_invalid_file_extension_rejected():
    # Invalid file extensions
    invalid_paths = [
        "image.txt",
        "image.png.txt",
        "image.sh",
        "image.png.exe",
        "image_no_extension",
    ]
    for path in invalid_paths:
        req = {
            "request_id": "REQ-123",
            "cmd": "inspect",
            "image_path": path
        }
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(P.json.dumps(req))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "invalid image file extension" in exc_info.value.msg
