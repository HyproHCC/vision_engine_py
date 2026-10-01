# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_protocol_rejects_path_traversal():
    req = json.dumps({
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "../secret.png"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req)
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info.value.msg


def test_protocol_rejects_unsupported_extension():
    req = json.dumps({
        "request_id": "REQ-002",
        "cmd": "inspect",
        "image_path": "sample.txt"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req)
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported image file extension" in exc_info.value.msg


def test_protocol_accepts_valid_image_extensions():
    for ext in [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"]:
        req = json.dumps({
            "request_id": "REQ-003",
            "cmd": "inspect",
            "image_path": f"C:/images/test{ext}"
        })
        parsed = parse_request(req)
        assert parsed["image_path"] == f"C:/images/test{ext}"
