# -*- coding: utf-8 -*-
import pytest
import json
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_valid_image_paths():
    # Valid configurations for inspect
    valid_payloads = [
        {
            "request_id": "REQ-01",
            "cmd": "inspect",
            "image_path": "D:/images/sample.png"
        },
        {
            "request_id": "REQ-02",
            "cmd": "inspect",
            "image_path": "/var/data/image.JPEG"
        },
        {
            "request_id": "REQ-03",
            "cmd": "teach",
            "image_path": "C:\\MyDir\\photo.bmp"
        },
        {
            "request_id": "REQ-04",
            "cmd": "teach",
            "image_path": "photo.tiff"
        },
        {
            "request_id": "REQ-05",
            "cmd": "inspect",
            "image_path": "photo.tif"
        },
        {
            "request_id": "REQ-06",
            "cmd": "inspect",
            "image_path": "photo.jpg"
        }
    ]
    for payload in valid_payloads:
        line = json.dumps(payload)
        parsed = parse_request(line)
        assert parsed["image_path"] == payload["image_path"]

def test_invalid_image_extensions():
    invalid_payloads = [
        {
            "request_id": "REQ-10",
            "cmd": "inspect",
            "image_path": "D:/images/sample.txt"
        },
        {
            "request_id": "REQ-11",
            "cmd": "inspect",
            "image_path": "/var/data/image.py"
        },
        {
            "request_id": "REQ-12",
            "cmd": "teach",
            "image_path": "C:\\MyDir\\photo.exe"
        },
        {
            "request_id": "REQ-13",
            "cmd": "teach",
            "image_path": "photo"
        },
        {
            "request_id": "REQ-14",
            "cmd": "inspect",
            "image_path": "photo."
        }
    ]
    for payload in invalid_payloads:
        line = json.dumps(payload)
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(line)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path file extension" in exc_info.value.msg

def test_path_traversal_detection():
    malicious_payloads = [
        {
            "request_id": "REQ-20",
            "cmd": "inspect",
            "image_path": "../etc/passwd.png"
        },
        {
            "request_id": "REQ-21",
            "cmd": "inspect",
            "image_path": "C:\\Windows\\..\\System32\\cmd.png"
        },
        {
            "request_id": "REQ-22",
            "cmd": "teach",
            "image_path": "images/../../secret.bmp"
        },
        {
            "request_id": "REQ-23",
            "cmd": "inspect",
            "image_path": "..\\test.tiff"
        }
    ]
    for payload in malicious_payloads:
        line = json.dumps(payload)
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(line)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal sequence" in exc_info.value.msg
