# -*- coding: utf-8 -*-
import pytest
import json
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_valid_image_paths_allowed():
    # Test allowing valid image extensions in image_path
    valid_extensions = ["png", "bmp", "jpg", "jpeg", "tif", "tiff", "PNG", "BMP", "Jpeg"]
    for ext in valid_extensions:
        req = {
            "request_id": "REQ-123",
            "cmd": "inspect",
            "image_path": f"D:/images/test.{ext}",
            "roi_mode": "AutoFrame"
        }
        parsed = parse_request(json.dumps(req))
        assert parsed["image_path"] == f"D:/images/test.{ext}"

def test_directory_traversal_rejected():
    # Test blocking paths that contain directory traversal sequences (..)
    traversal_paths = [
        "../test.png",
        "D:/images/../secret.png",
        "C:\\Windows\\..\\test.jpg",
        "test.png..",
        "..",
        "/etc/passwd/../test.bmp"
    ]
    for path in traversal_paths:
        req = {
            "request_id": "REQ-123",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg

def test_invalid_extensions_rejected():
    # Test blocking invalid/unsupported file extensions
    invalid_paths = [
        "test.txt",
        "test.exe",
        "test.png.txt",
        "test",
        "D:/images/test.py",
        "D:/images/test.png/",
        "D:/images/test.png\\",
    ]
    for path in invalid_paths:
        req = {
            "request_id": "REQ-123",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image extension" in exc_info.value.msg

def test_teach_command_also_validated():
    # Test that the teach command is subjected to the same security constraints
    req_traversal = {
        "request_id": "REQ-124",
        "cmd": "teach",
        "image_path": "../test.png",
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req_traversal))
    assert exc_info.value.code == E_BAD_FIELD

    req_invalid_ext = {
        "request_id": "REQ-124",
        "cmd": "teach",
        "image_path": "test.pdf",
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req_invalid_ext))
    assert exc_info.value.code == E_BAD_FIELD
