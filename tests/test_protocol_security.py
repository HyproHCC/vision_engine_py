# -*- coding: utf-8 -*-
"""協定層安全驗證單元測試。"""
import json
import pytest
from ve_server import protocol as P


def test_valid_image_path_extensions():
    valid_paths = [
        "C:/images/test.png",
        "D:/data/sample.BMP",
        "/tmp/photo.jpg",
        "relative/path/image.JPEG",
        "sample.tif",
        "sample.TIFF",
    ]
    for p in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p
        })
        parsed = P.parse_request(req_json)
        assert parsed["image_path"] == p


def test_path_traversal_rejection():
    invalid_paths = [
        "../etc/passwd.png",
        "C:/data/../secret.png",
        "../../test.jpg",
        "foo/bar/../baz.bmp",
    ]
    for cmd in ("inspect", "teach"):
        for p in invalid_paths:
            req_json = json.dumps({
                "request_id": "REQ-002",
                "cmd": cmd,
                "image_path": p
            })
            with pytest.raises(P.ProtocolError) as exc_info:
                P.parse_request(req_json)
            assert exc_info.value.code == P.E_BAD_FIELD
            assert "directory traversal" in exc_info.value.msg


def test_invalid_extension_rejection():
    invalid_paths = [
        "C:/data/secret.txt",
        "test.py",
        "image.png.exe",
        "script.sh",
        "no_extension",
    ]
    for cmd in ("inspect", "teach"):
        for p in invalid_paths:
            req_json = json.dumps({
                "request_id": "REQ-003",
                "cmd": cmd,
                "image_path": p
            })
            with pytest.raises(P.ProtocolError) as exc_info:
                P.parse_request(req_json)
            assert exc_info.value.code == P.E_BAD_FIELD
            assert "invalid image_path file extension" in exc_info.value.msg
