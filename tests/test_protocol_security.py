# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_parse_request_path_traversal():
    bad_req = {
        "request_id": "req-1",
        "cmd": "inspect",
        "image_path": "../secret_file.txt"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(bad_req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg


def test_parse_request_invalid_extension():
    bad_req = {
        "request_id": "req-2",
        "cmd": "inspect",
        "image_path": "valid_path/sample.exe"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(bad_req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported image extension" in exc_info.value.msg


def test_parse_request_valid_image():
    valid_req = {
        "request_id": "req-3",
        "cmd": "inspect",
        "image_path": "valid_path/sample.png"
    }
    req = parse_request(json.dumps(valid_req))
    assert req["image_path"] == "valid_path/sample.png"
