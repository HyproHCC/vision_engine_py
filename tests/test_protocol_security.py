# -*- coding: utf-8 -*-
"""Security protocol boundary validation unit tests."""
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_valid_image_paths():
    # A standard valid inspect request
    req = {
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "D:/images/piece_001.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    parsed = parse_request(json.dumps(req))
    assert parsed["image_path"] == "D:/images/piece_001.png"

    # Case-insensitivity check for valid extensions
    for ext in (".PNG", ".bmp", ".JPG", ".jpeg", ".TIF", ".TIFF"):
        req["image_path"] = f"D:/images/piece_001{ext}"
        parsed = parse_request(json.dumps(req))
        assert parsed["image_path"].endswith(ext)

def test_invalid_image_extensions():
    req = {
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "D:/images/piece_001.txt",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }

    # Text, python, executable extensions should be rejected
    for ext in (".txt", ".exe", ".py", ".sh", ".json", ".dll", ""):
        req["image_path"] = f"D:/images/piece_001{ext}"
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image extension" in exc_info.value.msg

def test_directory_traversal_rejection():
    req = {
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "D:/images/../../etc/passwd.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }

    traversal_paths = [
        "../piece.png",
        "D:/images/../piece.png",
        "..\\piece.png",
        "D:\\images\\..\\piece.png",
        "/etc/passwd/../piece.bmp"
    ]

    for path in traversal_paths:
        req["image_path"] = path
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal sequence is not allowed" in exc_info.value.msg
