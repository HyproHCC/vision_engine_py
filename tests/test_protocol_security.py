# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_paths():
    valid_paths = [
        "image.png",
        "C:/images/sample.BMP",
        "D:/data/test_01.jpg",
        "/var/app/test.jpeg",
        "sample.tif",
        "sample.tiff"
    ]
    for path in valid_paths:
        req_str = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path
        })
        parsed = parse_request(req_str)
        assert parsed["image_path"] == path


def test_path_traversal_rejection():
    traversal_paths = [
        "../secret.png",
        "C:/images/../etc/passwd.png",
        "dir/../../file.jpg",
        "..\\windows\\system32.png"
    ]
    for path in traversal_paths:
        req_str = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_invalid_extension_rejection():
    invalid_paths = [
        "script.py",
        "data.txt",
        "executable.exe",
        "no_extension_file"
    ]
    for path in invalid_paths:
        req_str = json.dumps({
            "request_id": "REQ-003",
            "cmd": "teach",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path file extension" in exc_info.value.msg
