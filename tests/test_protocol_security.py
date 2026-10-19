# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_protocol_image_path_valid():
    req = {
        "request_id": "123",
        "cmd": "inspect",
        "image_path": "C:/images/test.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    parsed = parse_request(pytest.importorskip("json").dumps(req))
    assert parsed["image_path"] == "C:/images/test.png"

def test_protocol_image_path_traversal():
    req = {
        "request_id": "123",
        "cmd": "inspect",
        "image_path": "C:/images/../secret.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    import json
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info.value.msg

def test_protocol_image_path_invalid_extension():
    req = {
        "request_id": "123",
        "cmd": "inspect",
        "image_path": "C:/images/test.exe",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    import json
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "invalid image extension" in exc_info.value.msg
