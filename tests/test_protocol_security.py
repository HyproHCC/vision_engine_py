# -*- coding: utf-8 -*-
"""協定層安全驗證單元測試：路徑穿透與副檔名白名單。"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_parse_request_valid_image_paths():
    """測試合法影像路徑與副檔名。"""
    valid_paths = [
        "C:/images/test.png",
        "D:/data/sample.bmp",
        "relative/path/image.jpg",
        "UPPERCASE_EXT.PNG",
        "photo.jpeg",
        "scan.tif",
        "scan.tiff",
    ]
    for path in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": path,
        })
        req = parse_request(req_json)
        assert req["image_path"] == path


def test_parse_request_path_traversal_rejected():
    """測試路徑穿透攻擊包含 '..' 被正確阻擋。"""
    invalid_paths = [
        "../test.png",
        "..\\test.png",
        "dir/../image.png",
        "C:/data/../../etc/passwd.png",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_parse_request_invalid_extension_rejected():
    """測試非允許的影像副檔名被正確阻擋。"""
    invalid_paths = [
        "test.txt",
        "config.json",
        "script.py",
        "image.png.exe",
        "no_ext",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "teach",
            "image_path": path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "extension" in exc_info.value.msg
