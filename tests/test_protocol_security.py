# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_valid_image_extensions():
    valid_paths = [
        "C:/images/test.png",
        "D:\\data\\sample.BMP",
        "image.jpg",
        "/tmp/photo.JPEG",
        "test.tif",
        "sample.TIFF",
    ]
    for p in valid_paths:
        raw = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        req = parse_request(raw)
        assert req["image_path"] == p


def test_invalid_image_extensions():
    invalid_paths = [
        "test.txt",
        "script.py",
        "executable.exe",
        "config.json",
        "noextension",
        "image.png.exe",
    ]
    for p in invalid_paths:
        raw = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(raw)
        assert exc_info.value.code == E_BAD_FIELD
        assert "extension not allowed" in exc_info.value.msg


def test_directory_traversal():
    traversal_paths = [
        "../etc/passwd.png",
        "..\\windows\\system32\\cmd.exe.png",
        "images/../../secret.jpg",
        "/var/www/../data/test.bmp",
    ]
    for p in traversal_paths:
        raw = json.dumps({
            "request_id": "REQ-1",
            "cmd": "teach",
            "image_path": p,
            "roi_mode": "AutoFrame"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(raw)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg
