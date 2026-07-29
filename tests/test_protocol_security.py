# -*- coding: utf-8 -*-
import pytest
import json
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_parse_request_valid_image_path():
    """測試合法影像路徑與副檔名"""
    req = {
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/img_001.png"
    }
    parsed = parse_request(json.dumps(req))
    assert parsed["image_path"] == "D:/VisionWork/img_001.png"

def test_parse_request_path_traversal():
    """測試阻擋目錄穿越 (Path Traversal)"""
    traversal_paths = [
        "D:/VisionWork/../../windows/system32/cmd.exe",
        "../test.png",
        "D:/VisionWork/..\\test.png",
        "D:/VisionWork/test../abc.png",  # 含有 ..
        "C:\\some\\path\\..\\file.jpg"
    ]
    for p in traversal_paths:
        req = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg

def test_parse_request_invalid_extension():
    """測試阻擋非預期之副檔名以防範非影像檔讀取"""
    invalid_paths = [
        "D:/VisionWork/img_001.txt",
        "D:/VisionWork/img_001.exe",
        "D:/VisionWork/img_001.json",
        "D:/VisionWork/img_001"  # 無副檔名
    ]
    for p in invalid_paths:
        req = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg

def test_parse_request_different_case_extensions():
    """測試不分大小寫之合法影像副檔名"""
    for ext in (".PNG", ".Bmp", ".JPEG", ".TIF", ".TIFF", ".jpg"):
        req = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": f"D:/VisionWork/img_001{ext}"
        }
        parsed = parse_request(json.dumps(req))
        assert parsed["image_path"].endswith(ext)
