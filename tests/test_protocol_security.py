# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_paths_pass():
    req_data = {
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "C:/images/test_01.png"
    }
    parsed = parse_request(json.dumps(req_data))
    assert parsed["image_path"] == "C:/images/test_01.png"

    for ext in [".bmp", ".jpg", ".jpeg", ".tif", ".tiff"]:
        req_data["image_path"] = f"test{ext}"
        assert parse_request(json.dumps(req_data))["image_path"] == f"test{ext}"


def test_path_traversal_rejected():
    traversal_paths = [
        "../test.png",
        "C:/images/../secret.png",
        "..\\test.png",
        "/var/log/../../etc/passwd.png"
    ]
    for path in traversal_paths:
        req_data = {
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": path
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req_data))
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_invalid_file_extensions_rejected():
    invalid_paths = [
        "test.txt",
        "script.py",
        "image.png.exe",
        "data.json",
        "image"
    ]
    for path in invalid_paths:
        req_data = {
            "request_id": "REQ-003",
            "cmd": "inspect",
            "image_path": path
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req_data))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid file extension" in exc_info.value.msg
