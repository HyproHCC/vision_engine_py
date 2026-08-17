# -*- coding: utf-8 -*-
"""Unit tests for ve_server/protocol.py security checks."""

import json
import pytest

from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_parse_request_valid_image_paths():
    valid_paths = [
        "C:/images/test.png",
        "D:/data/sample.BMP",
        "/tmp/photo.jpg",
        "image.JPEG",
        "sample.tif",
        "sample.TIFF",
    ]
    for p in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": p
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == p


def test_parse_request_invalid_file_extension():
    invalid_paths = [
        "config.json",
        "script.py",
        "executable.exe",
        "image.png.txt",
        "no_extension",
    ]
    for p in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": p
        })
        with pytest.raises(ProtocolError) as excinfo:
            parse_request(req_json)
        assert excinfo.value.code == E_BAD_FIELD
        assert "extension must be one of" in excinfo.value.msg


def test_parse_request_path_traversal():
    traversal_paths = [
        "../etc/passwd.png",
        "C:/images/../../secret.png",
        "..\\Windows\\System32\\calc.png",
        "dir/../file.bmp",
    ]
    for p in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": p
        })
        with pytest.raises(ProtocolError) as excinfo:
            parse_request(req_json)
        assert excinfo.value.code == E_BAD_FIELD
        assert "path traversal" in excinfo.value.msg
