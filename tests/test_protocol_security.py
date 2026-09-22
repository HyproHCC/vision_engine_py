# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_path_extensions():
    valid_paths = [
        "C:/images/test.png",
        "D:/data/sample.bmp",
        "E:/photos/cut.jpg",
        "F:/photos/cut.jpeg",
        "G:/raw/img.tif",
        "H:/raw/img.tiff",
        "C:/images/UPPER.PNG",
    ]
    for p in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p,
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == p


def test_path_traversal_rejected():
    invalid_paths = [
        "../etc/passwd.png",
        "C:/images/../../secret.png",
        "images/../test.bmp",
    ]
    for p in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": p,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_invalid_extension_rejected():
    invalid_exts = [
        "C:/data/script.py",
        "D:/data/exec.exe",
        "E:/data/config.json",
        "F:/data/image.png.txt",
        "G:/data/no_extension",
    ]
    for p in invalid_exts:
        req_json = json.dumps({
            "request_id": "REQ-003",
            "cmd": "inspect",
            "image_path": p,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "file extension not allowed" in exc_info.value.msg
