# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_path_extensions():
    valid_exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]
    for ext in valid_exts:
        req_str = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": f"C:/images/sample{ext}",
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        parsed = parse_request(req_str)
        assert parsed["image_path"] == f"C:/images/sample{ext}"


def test_path_traversal_rejection():
    invalid_paths = [
        "../secret.png",
        "C:/images/../etc/passwd.png",
        "..\\..\\system.png",
        "images/./../test.bmp"
    ]
    for p in invalid_paths:
        req_str = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": p
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_disallowed_image_extensions():
    invalid_files = [
        "C:/images/script.py",
        "C:/images/malware.exe",
        "C:/images/data.txt",
        "C:/images/noextension"
    ]
    for f in invalid_files:
        req_str = json.dumps({
            "request_id": "REQ-003",
            "cmd": "inspect",
            "image_path": f
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "extension must be one of" in exc_info.value.msg
