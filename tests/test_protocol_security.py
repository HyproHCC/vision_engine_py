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


def test_parse_request_path_traversal_rejected():
    req = {
        "request_id": "req-002",
        "cmd": "inspect",
        "image_path": "../etc/passwd.png"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg.lower()


def test_parse_request_unsupported_extension_rejected():
    req = {
        "request_id": "req-003",
        "cmd": "teach",
        "image_path": "C:/config/settings.json"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported image extension" in exc_info.value.msg.lower()
