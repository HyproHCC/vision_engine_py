# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_paths():
    for ext in [".png", ".PNG", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"]:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": f"C:/images/test{ext}"
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == f"C:/images/test{ext}"


def test_invalid_image_path_extension():
    req_json = json.dumps({
        "request_id": "REQ-2",
        "cmd": "inspect",
        "image_path": "C:/images/test.exe"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "invalid image_path extension" in exc_info.value.msg


def test_path_traversal():
    req_json = json.dumps({
        "request_id": "REQ-3",
        "cmd": "inspect",
        "image_path": "C:/images/../etc/passwd.png"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "relative path traversal" in exc_info.value.msg
