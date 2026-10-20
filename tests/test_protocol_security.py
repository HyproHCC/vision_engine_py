# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_protocol_valid_image_path():
    valid_req = {
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "C:/images/test.png",
        "roi_mode": "AutoFrame",
        "param_source": "None",
    }
    parsed = parse_request(json.dumps(valid_req))
    assert parsed["image_path"] == "C:/images/test.png"


def test_protocol_path_traversal_blocked():
    invalid_req = {
        "request_id": "REQ-002",
        "cmd": "inspect",
        "image_path": "C:/images/../secret/test.png",
        "roi_mode": "AutoFrame",
        "param_source": "None",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(invalid_req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg


def test_protocol_invalid_image_extension_blocked():
    invalid_req = {
        "request_id": "REQ-003",
        "cmd": "inspect",
        "image_path": "C:/images/test.exe",
        "roi_mode": "AutoFrame",
        "param_source": "None",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(invalid_req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "extension" in exc_info.value.msg


def test_protocol_valid_extensions_case_insensitive():
    for ext in [".png", ".PNG", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"]:
        req = {
            "request_id": "REQ-004",
            "cmd": "teach",
            "image_path": f"D:/data/sample{ext}",
            "roi_mode": "AutoFrame",
        }
        parsed = parse_request(json.dumps(req))
        assert parsed["image_path"] == f"D:/data/sample{ext}"
