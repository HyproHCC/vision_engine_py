# -*- coding: utf-8 -*-
"""協定層資安驗證單元測試：檔名副檔名與路徑穿透檢查。"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_valid_image_path_extensions():
    valid_exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]
    for ext in valid_exts:
        req_data = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": f"D:/images/sample{ext}",
            "roi_mode": "AutoFrame",
            "param_source": "None",
        }
        req = parse_request(json.dumps(req_data))
        assert req["image_path"] == f"D:/images/sample{ext}"


def test_invalid_image_path_extensions():
    invalid_paths = [
        "D:/images/sample.txt",
        "D:/images/sample.py",
        "D:/images/sample.exe",
        "D:/images/sample.json",
        "D:/images/sample",
    ]
    for path in invalid_paths:
        req_data = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None",
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req_data))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg


def test_path_traversal_prevention():
    traversal_paths = [
        "../etc/passwd.png",
        "..\\secret.png",
        "D:/images/../config.png",
        "C:\\images\\..\\system32.bmp",
        "../../test.jpeg",
    ]
    for path in traversal_paths:
        req_data = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None",
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req_data))
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal sequence" in exc_info.value.msg


def test_teach_cmd_path_validation():
    req_data = {
        "request_id": "REQ-002",
        "cmd": "teach",
        "image_path": "D:/teach/../secret.jpg",
        "roi_mode": "AutoFrame",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req_data))
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal sequence" in exc_info.value.msg
