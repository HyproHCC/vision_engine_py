# -*- coding: utf-8 -*-
"""協定層資安測試：驗證 image_path 的檔名副檔名白名單與目錄穿越防護。"""
import json
import pytest

from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_image_path_directory_traversal_rejected():
    req = {
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "../etc/passwd.png",
        "roi_mode": "AutoFrame",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info.value.msg


def test_image_path_unsupported_extension_rejected():
    invalid_paths = [
        "C:/data/test.exe",
        "C:/data/test.txt",
        "C:/data/test",
        "C:/data/test.png.bat",
    ]
    for path in invalid_paths:
        req = {
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image_path extension" in exc_info.value.msg


def test_image_path_valid_extensions_accepted():
    valid_paths = [
        "D:/images/sample.png",
        "D:/images/sample.PNG",
        "D:/images/sample.bmp",
        "D:/images/sample.jpg",
        "D:/images/sample.jpeg",
        "D:/images/sample.tif",
        "D:/images/sample.tiff",
    ]
    for path in valid_paths:
        req = {
            "request_id": "REQ-003",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
        }
        parsed = parse_request(json.dumps(req))
        assert parsed["image_path"] == path


def test_teach_cmd_security_validation():
    req = {
        "request_id": "REQ-004",
        "cmd": "teach",
        "image_path": "../../etc/shadow.jpg",
        "roi_mode": "AutoFrame",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req))
    assert exc_info.value.code == E_BAD_FIELD
