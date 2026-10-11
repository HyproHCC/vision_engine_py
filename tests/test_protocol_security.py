# -*- coding: utf-8 -*-
import json
import pytest
from ve_server import protocol as P


def test_valid_image_paths():
    req = {
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "C:/images/test.png"
    }
    parsed = P.parse_request(json.dumps(req))
    assert parsed["image_path"] == "C:/images/test.png"

    req_teach = {
        "request_id": "REQ-002",
        "cmd": "teach",
        "image_path": "/var/data/sample.BMP"
    }
    parsed_teach = P.parse_request(json.dumps(req_teach))
    assert parsed_teach["image_path"] == "/var/data/sample.BMP"


def test_path_traversal_rejected():
    req = {
        "request_id": "REQ-003",
        "cmd": "inspect",
        "image_path": "../etc/passwd.png"
    }
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(json.dumps(req))
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg


def test_invalid_extension_rejected():
    req = {
        "request_id": "REQ-004",
        "cmd": "inspect",
        "image_path": "C:/images/script.py"
    }
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(json.dumps(req))
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "invalid file extension" in exc_info.value.msg
