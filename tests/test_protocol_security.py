# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_path_extensions():
    valid_paths = [
        "C:/images/test.png",
        "D:/work/sample.BMP",
        "test.jpg",
        "image.jpeg",
        "doc.tif",
        "scan.TIFF",
    ]
    for p in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == p


def test_path_traversal_rejection():
    invalid_paths = [
        "../etc/passwd.png",
        "C:/images/../secret.jpg",
        "../../test.bmp",
    ]
    for p in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_invalid_extension_rejection():
    invalid_paths = [
        "image.txt",
        "script.py",
        "payload.exe",
        "no_ext_file",
        "image.png.txt",
    ]
    for p in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-003",
            "cmd": "teach",
            "image_path": p,
            "roi_mode": "AutoFrame",
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg
