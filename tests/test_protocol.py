# -*- coding: utf-8 -*-
import pytest
import json
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_protocol_valid_requests():
    # Valid inspect request
    req = {
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "D:/images/sample.png",
        "roi_mode": "AutoFrame"
    }
    parsed = parse_request(json.dumps(req))
    assert parsed["image_path"] == "D:/images/sample.png"

    # Case insensitive extension
    req["image_path"] = "D:/images/sample.BMP"
    parsed = parse_request(json.dumps(req))
    assert parsed["image_path"] == "D:/images/sample.BMP"

def test_protocol_directory_traversal():
    req = {
        "request_id": "REQ-002",
        "cmd": "inspect",
        "image_path": "D:/images/../../etc/passwd.png",
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(json.dumps(req))
    assert excinfo.value.code == E_BAD_FIELD
    assert "directory traversal" in excinfo.value.msg

def test_protocol_invalid_extension():
    req = {
        "request_id": "REQ-003",
        "cmd": "inspect",
        "image_path": "D:/images/sample.txt",
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(json.dumps(req))
    assert excinfo.value.code == E_BAD_FIELD
    assert "invalid image file extension" in excinfo.value.msg

def test_protocol_teach_validation():
    req = {
        "request_id": "REQ-004",
        "cmd": "teach",
        "image_path": "D:/images/../sample.png",  # contains ".."
        "roi_mode": "AutoFrame"
    }
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(json.dumps(req))
    assert excinfo.value.code == E_BAD_FIELD
