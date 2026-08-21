# -*- coding: utf-8 -*-
"""單元測試：驗證 ve_server/protocol.py 協定解析之安全性檢查。

1. 影像檔名副檔名白名單過濾 (.png, .bmp, .jpg, .jpeg, .tif, .tiff)
2. 路徑穿越 (Directory Traversal) 防護 ('..')
"""
import json
import pytest
from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_parse_request_valid_image_extensions():
    valid_paths = [
        "C:/images/test.png",
        "D:\\work\\sample.JPG",
        "/tmp/photo.jpeg",
        "image.bmp",
        "doc.tif",
        "scan.tiff",
    ]
    for p in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": p,
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == p


def test_parse_request_invalid_image_extensions():
    invalid_paths = [
        "script.py",
        "config.json",
        "malicious.exe",
        "data.txt",
        "image_no_ext",
    ]
    for p in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": p,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image file extension" in exc_info.value.msg


def test_parse_request_directory_traversal():
    traversal_paths = [
        "../etc/passwd.png",
        "..\\windows\\system32\\cmd.jpg",
        "C:\\app\\..\\secret\\img.png",
        "/var/www/../../etc/shadow.bmp",
    ]
    for p in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": p,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg
