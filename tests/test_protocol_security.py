# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_protocol_image_path_valid():
    req_str = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "C:/images/test.png"}'
    parsed = parse_request(req_str)
    assert parsed["image_path"] == "C:/images/test.png"

def test_protocol_image_path_traversal():
    req_str = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "../etc/passwd.png"}'
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_str)
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg

def test_protocol_image_path_invalid_extension():
    req_str = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "C:/images/test.exe"}'
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_str)
    assert exc_info.value.code == E_BAD_FIELD
    assert "invalid image_path extension" in exc_info.value.msg
