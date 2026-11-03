# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_path_extensions():
    valid_paths = [
        "C:/images/test.png",
        "D:/data/sample.BMP",
        "/var/images/photo.jpg",
        "image.jpeg",
        "sample.tif",
        "sample.TIFF",
    ]
    for p in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": p
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == p


def test_path_traversal_rejected():
    traversal_paths = [
        "../etc/passwd.png",
        "C:/app/../secret.jpg",
        "../../test.bmp",
        "images/..\\data.png",
    ]
    for p in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": p
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_invalid_image_extensions_rejected():
    invalid_paths = [
        "test.py",
        "script.sh",
        "data.json",
        "executable.exe",
        "no_extension",
        "image.png.txt",
    ]
    for p in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": p
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image extension" in exc_info.value.msg


def test_teach_command_image_path_security():
    req_json = json.dumps({
        "request_id": "REQ-2",
        "cmd": "teach",
        "image_path": "../invalid.py"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
