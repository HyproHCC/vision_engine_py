# -*- coding: utf-8 -*-
"""協定安全性單元測試：驗證 image_path 的副檔名限制與目錄穿越防護。"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_valid_image_extensions():
    valid_exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]
    for ext in valid_exts:
        req_data = {
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": f"C:/images/test_sample{ext}",
            "piece_id": "P001",
            "recipe_name": "R001",
            "roi_mode": "AutoFrame",
            "param_source": "None",
        }
        parsed = parse_request(json.dumps(req_data))
        assert parsed["image_path"] == f"C:/images/test_sample{ext}"


def test_path_traversal_rejected():
    invalid_paths = [
        "../secret.png",
        "C:/images/../secret.png",
        "..\\secret.bmp",
        "dir/../../etc/passwd.jpg",
    ]
    for path in invalid_paths:
        req_data = {
            "request_id": "REQ-0002",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None",
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req_data))
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_disallowed_file_extensions_rejected():
    invalid_paths = [
        "config.json",
        "data.txt",
        "script.py",
        "image.png.exe",
        "noextension",
    ]
    for path in invalid_paths:
        req_data = {
            "request_id": "REQ-0003",
            "cmd": "teach",
            "image_path": path,
            "recipe_name": "R001",
            "roi_mode": "AutoFrame",
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req_data))
        assert exc_info.value.code == E_BAD_FIELD
        assert "file extension" in exc_info.value.msg
