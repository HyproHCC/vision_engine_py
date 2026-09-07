# -*- coding: utf-8 -*-
"""協定安全性單元測試：驗證路徑穿越與影像副檔名限制。"""
import json
import pytest

from ve_server.protocol import (E_BAD_FIELD, E_BAD_JSON, E_UNKNOWN_CMD,
                                ProtocolError, parse_request)


def test_parse_request_valid_inspect():
    req_str = json.dumps({
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/sample.png",
        "piece_id": "P001",
        "recipe_name": "TYPE_A",
    })
    parsed = parse_request(req_str)
    assert parsed["cmd"] == "inspect"
    assert parsed["image_path"] == "D:/VisionWork/sample.png"


def test_parse_request_valid_extensions():
    valid_paths = [
        "images/test1.png",
        "images/test2.JPG",
        "images/test3.bmp",
        "images/test4.jpeg",
        "images/test5.tif",
        "images/test6.TIFF",
    ]
    for path in valid_paths:
        req_str = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
        })
        parsed = parse_request(req_str)
        assert parsed["image_path"] == path


def test_parse_request_path_traversal_rejected():
    traversal_paths = [
        "../secret.png",
        "D:/VisionWork/../secret.png",
        "folder/..\\file.png",
        "a/b/../../c.png",
    ]
    for path in traversal_paths:
        req_str = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal sequence '..' not allowed" in exc_info.value.msg


def test_parse_request_invalid_extensions_rejected():
    invalid_paths = [
        "script.py",
        "config.json",
        "malicious.exe",
        "image_without_extension",
        "test.png.bak",
    ]
    for path in invalid_paths:
        req_str = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid or unsupported image file extension" in exc_info.value.msg
