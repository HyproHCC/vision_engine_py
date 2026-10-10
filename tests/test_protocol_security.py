# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import (E_BAD_FIELD, ProtocolError, parse_request)


def test_parse_request_valid_image_path():
    req_json = json.dumps({
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/img_001.png"
    })
    parsed = parse_request(req_json)
    assert parsed["image_path"] == "D:/VisionWork/img_001.png"


def test_parse_request_path_traversal_rejected():
    req_json = json.dumps({
        "request_id": "REQ-002",
        "cmd": "inspect",
        "image_path": "../secret_file.png"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info.value.msg


def test_parse_request_invalid_extension_rejected():
    req_json = json.dumps({
        "request_id": "REQ-003",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/script.sh"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "invalid image_path extension" in exc_info.value.msg
