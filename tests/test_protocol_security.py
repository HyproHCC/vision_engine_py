# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_parse_request_valid_image_extensions():
    valid_paths = [
        "image.png",
        "IMAGE.BMP",
        "path/to/sample.jpg",
        "C:/images/test.jpeg",
        "sample.tif",
        "sample.TIFF",
    ]
    for p in valid_paths:
        req_str = json.dumps({"request_id": "REQ-1", "cmd": "inspect", "image_path": p})
        parsed = parse_request(req_str)
        assert parsed["image_path"] == p


def test_parse_request_path_traversal():
    invalid_paths = [
        "../etc/passwd.png",
        "images/../../secret.png",
        "..\\windows\\system32\\cmd.png",
    ]
    for p in invalid_paths:
        req_str = json.dumps({"request_id": "REQ-1", "cmd": "inspect", "image_path": p})
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_parse_request_disallowed_extension():
    invalid_paths = [
        "script.py",
        "data.txt",
        "malicious.exe",
        "image.png.exe",
        "noextension",
    ]
    for p in invalid_paths:
        req_str = json.dumps({"request_id": "REQ-1", "cmd": "inspect", "image_path": p})
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported extension" in exc_info.value.msg
