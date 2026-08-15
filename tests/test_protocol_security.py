# -*- coding: utf-8 -*-
"""Protocol validation and security tests."""
import json
import pytest

from ve_server.protocol import (
    E_BAD_FIELD,
    ProtocolError,
    parse_request,
)


def test_parse_request_valid_image_extensions():
    valid_exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]
    for ext in valid_exts:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": f"C:/images/sample{ext}",
            "roi_mode": "AutoFrame",
            "param_source": "None",
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == f"C:/images/sample{ext}"


def test_parse_request_path_traversal_rejected():
    traversal_paths = [
        "../etc/passwd.png",
        "C:/data/../secret/image.png",
        "..\\windows\\system32\\test.jpg",
        "/var/log/../../etc/shadow.bmp",
    ]
    for path in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None",
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_parse_request_invalid_extension_rejected():
    invalid_paths = [
        "C:/images/script.py",
        "C:/images/executable.exe",
        "C:/images/data.txt",
        "C:/images/noextension",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None",
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image_path extension" in exc_info.value.msg
