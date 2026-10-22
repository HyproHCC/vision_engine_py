# -*- coding: utf-8 -*-
"""Protocol layer security unit tests for path traversal and file extension validation."""
import json
import pytest

from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_path():
    req = {
        "request_id": "REQ-000001",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/sample_image.png",
        "roi_mode": "AutoFrame"
    }
    parsed = parse_request(json.dumps(req))
    assert parsed["image_path"] == "D:/VisionWork/sample_image.png"

    # Teach command
    req_teach = {
        "request_id": "REQ-000002",
        "cmd": "teach",
        "image_path": "C:\\Images\\teach.JPG",
        "roi_mode": "AutoFrame"
    }
    parsed_teach = parse_request(json.dumps(req_teach))
    assert parsed_teach["image_path"] == "C:\\Images\\teach.JPG"


def test_path_traversal_rejected():
    invalid_paths = [
        "../etc/passwd.png",
        "..\\Windows\\System32\\cmd.jpg",
        "D:/VisionWork/../secret.png",
        "C:\\App\\..\\config.bmp"
    ]
    for path in invalid_paths:
        req = {
            "request_id": "REQ-TRAVERSAL",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg.lower()


def test_invalid_image_extension_rejected():
    invalid_exts = [
        "D:/VisionWork/script.py",
        "D:/VisionWork/payload.exe",
        "D:/VisionWork/data.txt",
        "D:/VisionWork/no_extension"
    ]
    for path in invalid_exts:
        req = {
            "request_id": "REQ-BADEXT",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg.lower()
