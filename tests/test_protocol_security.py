# -*- coding: utf-8 -*-
"""單元測試：驗證協定層 (ve_server/protocol.py) 針對 image_path 的安全性檢查（檔尾副檔名與目錄遞迴）。"""

import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_parse_request_valid_image_paths():
    # 測試合法路徑與副檔名
    valid_paths = [
        "D:/VisionWork/img_001.png",
        "C:/images/piece.BMP",
        "/var/data/pic.jpg",
        "image.JPEG",
        "some_path/test.tif",
        "TIFF_file.tiff",
    ]
    for path in valid_paths:
        req = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        }
        parsed = parse_request(json.dumps(req))
        assert parsed["image_path"] == path

def test_parse_request_directory_traversal():
    # 測試目錄遞迴 (Directory Traversal)
    invalid_paths = [
        "../etc/passwd.png",
        "C:/images/../config.json",
        "/home/user/../../../../etc/shadow.jpg",
        "..\\windows\\system32\\cmd.exe.png",
    ]
    for path in invalid_paths:
        req = {
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg

def test_parse_request_invalid_extensions():
    # 測試不合法副檔名
    invalid_paths = [
        "D:/VisionWork/img_001.txt",
        "C:/images/piece.py",
        "/var/data/pic.json",
        "image", # 沒有副檔名
        "some_path/test.exe",
        "TIFF_file.tiff2",
    ]
    for path in invalid_paths:
        req = {
            "request_id": "REQ-003",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "image_path must have a valid image extension" in exc_info.value.msg

def test_parse_request_teach_command_security():
    # 確保 teach 指令也有套用安全檢查
    req_traversal = {
        "request_id": "REQ-004",
        "cmd": "teach",
        "image_path": "../img.png",
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req_traversal))
    assert exc_info.value.code == E_BAD_FIELD

    req_invalid_ext = {
        "request_id": "REQ-005",
        "cmd": "teach",
        "image_path": "/var/img.pdf",
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req_invalid_ext))
    assert exc_info.value.code == E_BAD_FIELD
