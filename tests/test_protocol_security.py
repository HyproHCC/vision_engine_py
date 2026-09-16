# -*- coding: utf-8 -*-
"""協定層資安驗證單元測試：檔名副檔名白名單與路徑穿越防禦。"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_parse_request_accepts_valid_image_extensions():
    valid_paths = [
        "C:/images/test.png",
        "sample.PNG",
        "/var/data/image.jpg",
        "photo.jpeg",
        "scan.bmp",
        "check.tif",
        "check.TIFF",
    ]
    for p in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-000001",
            "cmd": "inspect",
            "image_path": p,
            "piece_id": "P001",
            "recipe_name": "RECIPE_A",
            "roi_mode": "AutoFrame",
            "param_source": "None",
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == p


def test_parse_request_rejects_path_traversal():
    traversal_paths = [
        "../etc/passwd.png",
        "../../sensitive/data.jpg",
        "C:/foo/../bar/test.png",
        "..\\windows\\system32.bmp",
    ]
    for p in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-000002",
            "cmd": "inspect",
            "image_path": p,
            "piece_id": "P001",
            "recipe_name": "RECIPE_A",
            "roi_mode": "AutoFrame",
            "param_source": "None",
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_parse_request_rejects_invalid_image_extensions():
    invalid_paths = [
        "test.txt",
        "script.py",
        "data.json",
        "malicious.exe",
        "no_extension",
        "image.png.exe",
    ]
    for p in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-000003",
            "cmd": "teach",
            "image_path": p,
            "recipe_name": "RECIPE_A",
            "roi_mode": "AutoFrame",
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg
