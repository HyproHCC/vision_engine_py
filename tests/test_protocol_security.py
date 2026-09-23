# -*- coding: utf-8 -*-
"""Protocol security and boundary validation tests."""

import pytest
from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_valid_image_paths():
    """Verify valid image file extensions are accepted."""
    valid_paths = [
        "C:/images/test.png",
        "/var/data/image.BMP",
        "sample.jpg",
        "sample.jpeg",
        "sample.tif",
        "sample.TIFF",
    ]
    for p in valid_paths:
        req_str = f'{{"request_id": "REQ-1", "cmd": "inspect", "image_path": "{p}"}}'
        req = parse_request(req_str)
        assert req["image_path"] == p


def test_path_traversal_rejected():
    """Verify directory traversal sequences ('..') are rejected."""
    traversal_paths = [
        "../etc/passwd.png",
        "C:/images/../secret.png",
        "..",
        "a/b/../c.jpg",
    ]
    for p in traversal_paths:
        req_str = f'{{"request_id": "REQ-1", "cmd": "inspect", "image_path": "{p}"}}'
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_invalid_image_extension_rejected():
    """Verify non-image extensions are rejected."""
    invalid_paths = [
        "test.txt",
        "script.py",
        "executable.exe",
        "no_extension",
        "image.png.bak",
    ]
    for p in invalid_paths:
        req_str = f'{{"request_id": "REQ-1", "cmd": "inspect", "image_path": "{p}"}}'
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "extension" in exc_info.value.msg


def test_teach_command_path_validation():
    """Verify teach command also validates image_path."""
    req_str = '{"request_id": "REQ-1", "cmd": "teach", "image_path": "../bad.png"}'
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_str)
    assert exc_info.value.code == E_BAD_FIELD

    valid_teach = '{"request_id": "REQ-1", "cmd": "teach", "image_path": "teach.png"}'
    req = parse_request(valid_teach)
    assert req["cmd"] == "teach"
