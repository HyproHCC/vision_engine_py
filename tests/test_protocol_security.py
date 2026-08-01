# -*- coding: utf-8 -*-
import pytest
import json
from ve_server import protocol as P

def test_valid_image_paths():
    """Tests that normal, valid image paths pass parsing successfully."""
    valid_paths = [
        "image.png",
        "folder/subfolder/test_image.bmp",
        "C:\\images\\capture.jpg",
        "/var/data/images/photo.jpeg",
        "image.tif",
        "image.TIFF",  # case-insensitive check
    ]
    for path in valid_paths:
        req = {
            "request_id": "req-123",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        # Should parse successfully without raising ProtocolError
        parsed = P.parse_request(json.dumps(req))
        assert parsed["image_path"] == path

def test_directory_traversal_detection():
    """Tests that directory traversal sequences in image_path are rejected."""
    traversal_paths = [
        "../image.png",
        "images/../../etc/passwd.png",
        "..\\image.bmp",
        "some/path/..",
    ]
    for path in traversal_paths:
        req = {
            "request_id": "req-123",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(json.dumps(req))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "directory traversal detected" in exc_info.value.msg

def test_invalid_file_extensions():
    """Tests that image_path with disallowed file extensions are rejected."""
    invalid_paths = [
        "image.txt",
        "image.exe",
        "image.png.exe",
        "image.pdf",
        "image", # no extension
        "image.png.txt",
    ]
    for path in invalid_paths:
        req = {
            "request_id": "req-123",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(json.dumps(req))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "invalid file extension in image_path" in exc_info.value.msg

def test_missing_or_empty_image_path():
    """Tests that missing or empty image_path fields are rejected."""
    # Empty string
    req_empty = {
        "request_id": "req-123",
        "cmd": "inspect",
        "image_path": "",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(json.dumps(req_empty))
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "missing image_path" in exc_info.value.msg

    # Non-string value
    req_invalid_type = {
        "request_id": "req-123",
        "cmd": "inspect",
        "image_path": 1234,
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(json.dumps(req_invalid_type))
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "missing image_path" in exc_info.value.msg
