# -*- coding: utf-8 -*-
"""協定安全性單元測試：驗證 image_path 檔名副檔名與路徑遍歷防護。"""
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_paths():
    valid_paths = [
        "C:/images/test.png",
        "sample.JPG",
        "folder/image.bmp",
        "test.jpeg",
        "test.tif",
        "test.tiff",
    ]
    for path in valid_paths:
        req_json = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": path
        })
        req = parse_request(req_json)
        assert req["image_path"] == path


def test_path_traversal_blocked():
    invalid_paths = [
        "../etc/passwd.png",
        "C:/data/../secret.png",
        "..\\windows\\system32\\cmd.exe.bmp",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_disallowed_file_extension():
    invalid_paths = [
        "test.txt",
        "exploit.exe",
        "script.py",
        "no_extension",
        "image.png.exe",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "req-1",
            "cmd": "teach",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "valid image extension" in exc_info.value.msg
