# -*- coding: utf-8 -*-
"""單元測試：驗證 ve_server/protocol.py 的安全性檢查與輸入驗證。"""
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_protocol_accepts_valid_image_paths():
    valid_paths = [
        "D:/VisionWork/img_20260706_101500_001.png",
        "C:\\Images\\sample.BMP",
        "test.jpg",
        "folder/image.jpeg",
        "data/sample.tif",
        "data/sample.tiff",
    ]
    for path in valid_paths:
        req_str = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
            "piece_id": "P001",
            "recipe_name": "TYPE_A",
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        parsed = parse_request(req_str)
        assert parsed["image_path"] == path


def test_protocol_rejects_path_traversal():
    invalid_paths = [
        "../etc/passwd.png",
        "D:/VisionWork/../secret.png",
        "C:\\VisionWork\\..\\config.json",
        "folder/../../file.bmp",
    ]
    for path in invalid_paths:
        req_str = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": path,
            "piece_id": "P001",
            "recipe_name": "TYPE_A",
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg.lower()


def test_protocol_rejects_disallowed_file_extensions():
    invalid_paths = [
        "config.json",
        "script.sh",
        "malicious.exe",
        "no_extension",
        "image.png.txt",
    ]
    for path in invalid_paths:
        req_str = json.dumps({
            "request_id": "REQ-003",
            "cmd": "teach",
            "image_path": path,
            "recipe_name": "TYPE_A",
            "roi_mode": "AutoFrame"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image_path file extension" in exc_info.value.msg.lower()
