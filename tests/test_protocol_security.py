# -*- coding: utf-8 -*-
import json
import pytest
from ve_server import protocol as P


def test_valid_image_path_extensions():
    valid_paths = [
        "C:/images/test.png",
        "C:/images/test.BMP",
        "D:/data/image.jpg",
        "D:/data/image.jpeg",
        "/tmp/sample.tif",
        "/tmp/sample.TIFF",
    ]
    for path in valid_paths:
        raw_inspect = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": path
        })
        req_inspect = P.parse_request(raw_inspect)
        assert req_inspect["image_path"] == path

        raw_teach = json.dumps({
            "request_id": "req-2",
            "cmd": "teach",
            "image_path": path
        })
        req_teach = P.parse_request(raw_teach)
        assert req_teach["image_path"] == path


def test_path_traversal_rejected():
    invalid_paths = [
        "../etc/passwd.png",
        "C:/images/../../secret.bmp",
        "folder/../image.jpg",
        "..\\windows\\system32\\cmd.png",
    ]
    for path in invalid_paths:
        raw = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(raw)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_invalid_extensions_rejected():
    invalid_paths = [
        "C:/images/script.py",
        "C:/images/data.txt",
        "C:/images/exec.exe",
        "C:/images/no_extension",
        "C:/images/image.png.exe",
    ]
    for path in invalid_paths:
        raw = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(raw)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "file extension" in exc_info.value.msg
