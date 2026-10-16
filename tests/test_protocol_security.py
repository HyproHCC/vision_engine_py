# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_path_extensions():
    for ext in (".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG"):
        req_json = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": f"C:/images/sample{ext}"
        })
        req = parse_request(req_json)
        assert req["image_path"] == f"C:/images/sample{ext}"


def test_path_traversal_rejected():
    invalid_paths = [
        "../secret.png",
        "C:/images/../config.json",
        "../../etc/passwd.png",
        "images/..\\system32\\cmd.exe.png",
    ]
    for p in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": p
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "image_path cannot contain '..'" in exc_info.value.msg


def test_invalid_image_path_extensions():
    invalid_paths = [
        "C:/images/test.txt",
        "C:/images/test.exe",
        "C:/images/test.py",
        "C:/images/test",
    ]
    for p in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-003",
            "cmd": "inspect",
            "image_path": p
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg
