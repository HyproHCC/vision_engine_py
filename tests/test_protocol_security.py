# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_parse_request_valid_image_path():
    valid_req = {
        "request_id": "req-001",
        "cmd": "inspect",
        "image_path": "images/test_piece.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    parsed = parse_request(json.dumps(valid_req))
    assert parsed["image_path"] == "images/test_piece.png"


def test_parse_request_path_traversal_rejected():
    invalid_req = {
        "request_id": "req-002",
        "cmd": "inspect",
        "image_path": "../etc/passwd",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(invalid_req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg


def test_parse_request_invalid_extension_rejected():
    invalid_req = {
        "request_id": "req-003",
        "cmd": "inspect",
        "image_path": "payload.py",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(invalid_req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported image file extension" in exc_info.value.msg
