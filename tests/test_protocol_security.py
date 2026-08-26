# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import (
    E_BAD_FIELD,
    ProtocolError,
    parse_request,
)


def test_path_traversal_rejected():
    payload = json.dumps({
        "request_id": "req-1",
        "cmd": "inspect",
        "image_path": "../etc/passwd.png"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(payload)
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg


def test_invalid_extension_rejected():
    payload = json.dumps({
        "request_id": "req-2",
        "cmd": "inspect",
        "image_path": "C:/images/test.txt"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(payload)
    assert exc_info.value.code == E_BAD_FIELD
    assert "extension must be one of" in exc_info.value.msg


def test_valid_image_path_accepted():
    for ext in [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG"]:
        payload = json.dumps({
            "request_id": "req-3",
            "cmd": "inspect",
            "image_path": f"C:/images/sample{ext}"
        })
        parsed = parse_request(payload)
        assert parsed["image_path"] == f"C:/images/sample{ext}"
