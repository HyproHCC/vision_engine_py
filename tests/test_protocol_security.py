# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_extensions():
    for ext in [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": f"C:/images/test{ext}"
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == f"C:/images/test{ext}"


def test_invalid_image_extension():
    for ext in [".txt", ".exe", ".sh", ".json"]:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": f"C:/images/test{ext}"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image_path extension" in exc_info.value.msg


def test_path_traversal_blocked():
    traversal_paths = [
        "../etc/passwd.png",
        "C:/images/../secret.png",
        "..\\Windows\\system32.png"
    ]
    for path in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg
