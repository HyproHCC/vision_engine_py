# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import (
    E_BAD_FIELD,
    ProtocolError,
    parse_request,
)


def test_parse_request_valid_image_paths():
    valid_paths = [
        "C:/images/sample.png",
        "D:/test/image.BMP",
        "/var/data/pic.jpg",
        "relative_path/sample.jpeg",
        "test.tif",
        "test.tiff",
    ]
    for path in valid_paths:
        req_json = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": path,
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == path


def test_parse_request_path_traversal_rejected():
    invalid_paths = [
        "../etc/passwd.png",
        "C:/data/../secret.png",
        "sub/../../test.jpg",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "req-2",
            "cmd": "inspect",
            "image_path": path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_parse_request_invalid_extension_rejected():
    invalid_paths = [
        "C:/images/script.py",
        "D:/test/data.txt",
        "image_without_extension",
        "malicious.exe",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "req-3",
            "cmd": "inspect",
            "image_path": path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image file extension" in exc_info.value.msg
