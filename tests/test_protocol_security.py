# -*- coding: utf-8 -*-
"""協定安全性與輸入驗證單元測試。"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_parse_request_valid_image_extensions():
    valid_paths = [
        "C:/images/test.png",
        "/var/data/sample.bmp",
        "photo.jpg",
        "photo.jpeg",
        "image.tif",
        "IMAGE.TIFF",
    ]
    for p in valid_paths:
        req_inspect = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p,
        })
        parsed = parse_request(req_inspect)
        assert parsed["image_path"] == p

        req_teach = json.dumps({
            "request_id": "REQ-002",
            "cmd": "teach",
            "image_path": p,
        })
        parsed_teach = parse_request(req_teach)
        assert parsed_teach["image_path"] == p


def test_parse_request_rejects_path_traversal():
    traversal_paths = [
        "../etc/passwd.png",
        "C:/images/../../secret.bmp",
        "foo/bar/../baz.jpg",
    ]
    for p in traversal_paths:
        req = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_parse_request_rejects_invalid_file_extension():
    invalid_paths = [
        "image.txt",
        "script.py",
        "executable.exe",
        "noextension",
        "malicious.png.exe",
    ]
    for p in invalid_paths:
        req = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg
