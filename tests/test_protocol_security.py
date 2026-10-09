# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_parse_request_valid_image_path():
    req_json = (
        '{"request_id": "REQ-001", "cmd": "inspect", '
        '"image_path": "C:/images/test.png", "param_source": "None"}'
    )
    req = parse_request(req_json)
    assert req["image_path"] == "C:/images/test.png"


def test_parse_request_path_traversal_rejected():
    req_json = (
        '{"request_id": "REQ-002", "cmd": "inspect", '
        '"image_path": "C:/images/../etc/passwd.png", "param_source": "None"}'
    )
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(req_json)
    assert excinfo.value.code == E_BAD_FIELD
    assert "path traversal" in excinfo.value.msg


def test_parse_request_invalid_extension_rejected():
    req_json = (
        '{"request_id": "REQ-003", "cmd": "inspect", '
        '"image_path": "C:/images/test.exe", "param_source": "None"}'
    )
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(req_json)
    assert excinfo.value.code == E_BAD_FIELD
    assert "extension" in excinfo.value.msg


def test_parse_request_case_insensitive_extension():
    req_json = (
        '{"request_id": "REQ-004", "cmd": "inspect", '
        '"image_path": "C:/images/test.PNG", "param_source": "None"}'
    )
    req = parse_request(req_json)
    assert req["image_path"] == "C:/images/test.PNG"
