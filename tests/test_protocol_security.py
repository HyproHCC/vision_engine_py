# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_parse_request_image_path_valid_extension():
    req = {
        "request_id": "REQ-0001",
        "cmd": "inspect",
        "image_path": "C:/images/test.png",
        "roi_mode": "AutoFrame",
    }
    parsed = parse_request(json_stringify(req))
    assert parsed["image_path"] == "C:/images/test.png"


def test_parse_request_image_path_invalid_extension():
    req = {
        "request_id": "REQ-0002",
        "cmd": "inspect",
        "image_path": "C:/images/test.exe",
        "roi_mode": "AutoFrame",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json_stringify(req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "extension" in exc_info.value.msg.lower() or "invalid image file" in exc_info.value.msg.lower()


def test_parse_request_image_path_traversal():
    req = {
        "request_id": "REQ-0003",
        "cmd": "inspect",
        "image_path": "../../etc/passwd.png",
        "roi_mode": "AutoFrame",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json_stringify(req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "traversal" in exc_info.value.msg.lower() or "invalid image path" in exc_info.value.msg.lower()


def json_stringify(d):
    import json
    return json.dumps(d)
