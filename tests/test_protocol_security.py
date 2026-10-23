# -*- coding: utf-8 -*-
"""協定資安檢查單元測試。

測試 ve_server.protocol 對輸入欄位的安全性防護：
1. 目錄穿越 (Directory Traversal) 防護
2. 不允許之檔案副檔名過濾
3. ASCII 欄位限制
"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_valid_inspect_request():
    req_json = json.dumps({
        "request_id": "REQ-0001",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/image.png",
        "piece_id": "P001",
        "recipe_name": "RECIPE_A"
    })
    parsed = parse_request(req_json)
    assert parsed["cmd"] == "inspect"
    assert parsed["image_path"] == "D:/VisionWork/image.png"


def test_valid_teach_request():
    req_json = json.dumps({
        "request_id": "REQ-0002",
        "cmd": "teach",
        "image_path": "C:/data/sample.BMP"
    })
    parsed = parse_request(req_json)
    assert parsed["cmd"] == "teach"


@pytest.mark.parametrize("path_traversal_path", [
    "../secret.png",
    "C:/images/../etc/passwd.jpg",
    "..\\windows\\system32\\cmd.png",
    "D:/data/dir/../../test.tiff"
])
def test_path_traversal_rejected(path_traversal_path):
    req_json = json.dumps({
        "request_id": "REQ-0003",
        "cmd": "inspect",
        "image_path": path_traversal_path
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info.value.msg


@pytest.mark.parametrize("invalid_ext_path", [
    "D:/VisionWork/script.py",
    "D:/VisionWork/data.txt",
    "D:/VisionWork/image.png.exe",
    "D:/VisionWork/image",
    "D:/VisionWork/config.json"
])
def test_disallowed_extension_rejected(invalid_ext_path):
    req_json = json.dumps({
        "request_id": "REQ-0004",
        "cmd": "inspect",
        "image_path": invalid_ext_path
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "extension not allowed" in exc_info.value.msg


def test_non_ascii_field_rejected():
    req_json = json.dumps({
        "request_id": "REQ-0005",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/圖片.png"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "non-ASCII" in exc_info.value.msg
