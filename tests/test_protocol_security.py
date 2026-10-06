# -*- coding: utf-8 -*-
"""Protocol boundary security tests for ve_server.protocol."""
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_extensions():
    valid_paths = [
        "C:/images/sample.png",
        "D:\\data\\image.BMP",
        "/tmp/photo.JPG",
        "relative/path/test.jpeg",
        "img.tif",
        "img.TIFF",
    ]
    for p in valid_paths:
        raw = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        req = parse_request(raw)
        assert req["image_path"] == p


def test_path_traversal_rejection():
    invalid_paths = [
        "../secret.png",
        "../../etc/passwd.png",
        "C:/app/../config.png",
        "images/..\\system32.png",
    ]
    for p in invalid_paths:
        raw = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(raw)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_disallowed_file_extension_rejection():
    invalid_paths = [
        "test.txt",
        "script.py",
        "image.png.exe",
        "noextension",
        "payload.sh",
    ]
    for p in invalid_paths:
        raw = json.dumps({
            "request_id": "REQ-003",
            "cmd": "teach",
            "image_path": p,
            "roi_mode": "AutoFrame"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(raw)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image extension" in exc_info.value.msg
