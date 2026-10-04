# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import (
    parse_request, ProtocolError, E_BAD_FIELD, E_BAD_JSON, E_UNKNOWN_CMD
)


def test_parse_request_valid_inspect():
    req_json = json.dumps({
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "C:/images/test.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    })
    req = parse_request(req_json)
    assert req["request_id"] == "REQ-001"
    assert req["cmd"] == "inspect"


def test_parse_request_valid_extensions():
    exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]
    for ext in exts:
        req_json = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": f"C:/images/test{ext}",
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        req = parse_request(req_json)
        assert req["image_path"].endswith(ext)


def test_parse_request_path_traversal_rejected():
    traversal_paths = [
        "../etc/passwd.png",
        "C:/images/../secret.png",
        "..\\windows\\system32.png",
        "dir/../../file.png"
    ]
    for path in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_parse_request_disallowed_extension_rejected():
    invalid_paths = [
        "C:/images/test.exe",
        "C:/images/test.txt",
        "C:/images/test.py",
        "C:/images/test.png.exe",
        "C:/images/test_no_ext"
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "extension not allowed" in exc_info.value.msg


def test_parse_request_non_ascii_rejected():
    req_json = json.dumps({
        "request_id": "REQ-001",
        "cmd": "inspect",
        "image_path": "C:/images/測試.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "contains non-ASCII" in exc_info.value.msg
