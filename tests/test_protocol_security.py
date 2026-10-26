# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_path_allowed():
    req_json = json.dumps({
        "request_id": "REQ-100",
        "cmd": "inspect",
        "image_path": "C:/images/sample.png"
    })
    parsed = parse_request(req_json)
    assert parsed["image_path"] == "C:/images/sample.png"


def test_path_traversal_rejected():
    # Test forward slash path traversal
    req_json1 = json.dumps({
        "request_id": "REQ-101",
        "cmd": "inspect",
        "image_path": "../etc/passwd.png"
    })
    with pytest.raises(ProtocolError) as exc_info1:
        parse_request(req_json1)
    assert exc_info1.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info1.value.msg

    # Test backslash path traversal
    req_json2 = json.dumps({
        "request_id": "REQ-102",
        "cmd": "teach",
        "image_path": "..\\windows\\system32\\cmd.jpg"
    })
    with pytest.raises(ProtocolError) as exc_info2:
        parse_request(req_json2)
    assert exc_info2.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info2.value.msg


def test_disallowed_extension_rejected():
    req_json = json.dumps({
        "request_id": "REQ-103",
        "cmd": "inspect",
        "image_path": "C:/script/malicious.py"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "extension not allowed" in exc_info.value.msg
