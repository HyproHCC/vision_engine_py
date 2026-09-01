# -*- coding: utf-8 -*-
"""Unit tests for TCP protocol security input validations."""

import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_protocol_security_path_traversal():
    """Verify that path traversal sequences ('..') in image_path are rejected."""
    traversal_paths = [
        "../etc/passwd.png",
        "../../secret.jpg",
        "C:\\..\\Windows\\System32\\test.bmp",
        "images/../other.png",
    ]
    for path in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": path,
            "recipe_name": "TYPE_A",
            "roi_mode": "AutoFrame",
        })
        with pytest.raises(ProtocolError) as excinfo:
            parse_request(req_json)
        assert excinfo.value.code == E_BAD_FIELD
        assert "directory traversal" in excinfo.value.msg


def test_protocol_security_unallowed_extension():
    """Verify that disallowed file extensions are rejected."""
    invalid_paths = [
        "image.sh",
        "payload.exe",
        "script.py",
        "data.txt",
        "noextension",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0002",
            "cmd": "inspect",
            "image_path": path,
            "recipe_name": "TYPE_A",
            "roi_mode": "AutoFrame",
        })
        with pytest.raises(ProtocolError) as excinfo:
            parse_request(req_json)
        assert excinfo.value.code == E_BAD_FIELD
        assert "unallowed extension" in excinfo.value.msg


def test_protocol_security_allowed_extensions():
    """Verify that allowed image extensions pass validation."""
    valid_paths = [
        "sample.png",
        "sample.PNG",
        "image.bmp",
        "photo.jpg",
        "photo.jpeg",
        "file.tif",
        "file.tiff",
    ]
    for path in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0003",
            "cmd": "inspect",
            "image_path": path,
            "recipe_name": "TYPE_A",
            "roi_mode": "AutoFrame",
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == path
