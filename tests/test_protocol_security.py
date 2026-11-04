# -*- coding: utf-8 -*-
"""協定安全單元測試：驗證路徑穿越防護與影像副檔名檢查。"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_parse_request_valid_image_path():
    req = {
        "request_id": "req-001",
        "cmd": "inspect",
        "image_path": "C:/images/sample_01.png"
    }
    parsed = parse_request(json.dumps(req))
    assert parsed["image_path"] == "C:/images/sample_01.png"


def test_parse_request_valid_extensions():
    for ext in [".png", ".PNG", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"]:
        req = {
            "request_id": "req-002",
            "cmd": "teach",
            "image_path": f"C:/images/sample{ext}"
        }
        parsed = parse_request(json.dumps(req))
        assert parsed["image_path"].endswith(ext)


def test_parse_request_path_traversal_rejected():
    for traversal_path in [
        "../etc/passwd.png",
        "C:/images/../secret.png",
        "..\\windows\\system32\\cmd.jpg",
        "sub/../../test.bmp"
    ]:
        req = {
            "request_id": "req-003",
            "cmd": "inspect",
            "image_path": traversal_path
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg.lower()


def test_parse_request_unsupported_extension_rejected():
    for invalid_path in [
        "C:/images/sample.txt",
        "C:/images/config.json",
        "C:/images/script.py",
        "C:/images/sample.exe"
    ]:
        req = {
            "request_id": "req-004",
            "cmd": "teach",
            "image_path": invalid_path
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image extension" in exc_info.value.msg.lower()
