# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_parse_request_valid_extensions():
    # Valid extensions
    for ext in (".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".BMP"):
        req_str = json.dumps({
            "request_id": "REQ-123",
            "cmd": "inspect",
            "image_path": f"C:/images/test{ext}",
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        parsed = parse_request(req_str)
        assert parsed["image_path"] == f"C:/images/test{ext}"

def test_parse_request_invalid_extensions():
    # Invalid extensions / paths
    invalid_paths = [
        "C:/Windows/System32/drivers/etc/hosts",
        "../../etc/passwd",
        "test.txt",
        "test.png.txt",
        "image_path_without_extension",
        "test.png\x00.txt",
        "test.png\\",
        "test.jpeg2000"
    ]
    for path in invalid_paths:
        req_str = json.dumps({
            "request_id": "REQ-123",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "image_path must have a valid image file extension" in exc_info.value.msg

def test_parse_request_teach_valid_and_invalid():
    # Test valid extension for teach command
    req_str_valid = json.dumps({
        "request_id": "REQ-124",
        "cmd": "teach",
        "image_path": "test.bmp",
        "roi_mode": "AutoFrame"
    })
    parsed = parse_request(req_str_valid)
    assert parsed["image_path"] == "test.bmp"

    # Test invalid extension for teach command
    req_str_invalid = json.dumps({
        "request_id": "REQ-124",
        "cmd": "teach",
        "image_path": "test.gif",
        "roi_mode": "AutoFrame"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_str_invalid)
    assert exc_info.value.code == E_BAD_FIELD
