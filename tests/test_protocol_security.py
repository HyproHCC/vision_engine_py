# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_protocol_security_path_traversal():
    req_traversal = {
        "request_id": "req-1",
        "cmd": "inspect",
        "image_path": "../etc/passwd.png",
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(str(req_traversal).replace("'", '"'))
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg.lower()


def test_protocol_security_invalid_extension():
    req_invalid_ext = {
        "request_id": "req-2",
        "cmd": "inspect",
        "image_path": "test.txt",
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(str(req_invalid_ext).replace("'", '"'))
    assert exc_info.value.code == E_BAD_FIELD
    assert "invalid image file extension" in exc_info.value.msg.lower()


def test_protocol_security_valid_image_path():
    req_valid = {
        "request_id": "req-3",
        "cmd": "inspect",
        "image_path": "testdata/valid_image.png",
        "roi_mode": "AutoFrame"
    }
    parsed = parse_request(str(req_valid).replace("'", '"'))
    assert parsed["image_path"] == "testdata/valid_image.png"


def test_protocol_security_non_ascii_field():
    req_non_ascii = {
        "request_id": "req-4",
        "cmd": "inspect",
        "image_path": "testdata/測試.png",
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(str(req_non_ascii).replace("'", '"'))
    assert exc_info.value.code == E_BAD_FIELD
    assert "non-ascii" in exc_info.value.msg.lower()
