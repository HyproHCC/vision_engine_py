# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import (E_BAD_FIELD, ProtocolError, parse_request)


def test_valid_image_path():
    valid_req = json.dumps({
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "C:/images/test.png"
    })
    parsed = parse_request(valid_req)
    assert parsed["image_path"] == "C:/images/test.png"


def test_path_traversal_rejected():
    traversal_req = json.dumps({
        "request_id": "REQ-002",
        "cmd": "inspect",
        "image_path": "../secret/config.json"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(traversal_req)
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal disallowed" in exc_info.value.msg


def test_unsupported_file_extension_rejected():
    invalid_ext_req = json.dumps({
        "request_id": "REQ-003",
        "cmd": "teach",
        "image_path": "C:/images/script.exe"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(invalid_ext_req)
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported extension" in exc_info.value.msg
