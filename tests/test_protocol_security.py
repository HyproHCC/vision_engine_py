# -*- coding: utf-8 -*-
"""協定層資安測試：驗證 image_path 的檔名副檔名與路徑穿透檢查。"""
import json
import pytest

from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_extensions_pass():
    valid_exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]
    for ext in valid_exts:
        raw = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": f"C:/images/test{ext}"
        })
        req = parse_request(raw)
        assert req["image_path"] == f"C:/images/test{ext}"


def test_path_traversal_rejected():
    invalid_paths = [
        "../secret.png",
        "C:/images/../secret.png",
        "..\\secret.png",
        "folder/../../etc/passwd.png"
    ]
    for p in invalid_paths:
        raw = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": p
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(raw)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_invalid_extensions_rejected():
    invalid_files = [
        "C:/images/test.txt",
        "C:/images/test.exe",
        "C:/images/test.py",
        "C:/images/test.json",
        "C:/images/test"
    ]
    for f in invalid_files:
        raw = json.dumps({
            "request_id": "REQ-003",
            "cmd": "teach",
            "image_path": f
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(raw)
        assert exc_info.value.code == E_BAD_FIELD
        assert "extension" in exc_info.value.msg
