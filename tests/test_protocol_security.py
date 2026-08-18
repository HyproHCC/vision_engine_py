# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import (
    E_BAD_FIELD,
    ProtocolError,
    parse_request,
)


def test_valid_image_path():
    req = {
        "request_id": "REQ-000001",
        "cmd": "inspect",
        "image_path": "C:/VisionWork/image001.png",
        "roi_mode": "AutoFrame",
        "param_source": "None",
    }
    parsed = parse_request(json.dumps(req))
    assert parsed["image_path"] == "C:/VisionWork/image001.png"


def test_valid_upper_case_extension():
    req = {
        "request_id": "REQ-000002",
        "cmd": "teach",
        "image_path": "D:/data/teach_sample.BMP",
        "roi_mode": "AutoFrame",
    }
    parsed = parse_request(json.dumps(req))
    assert parsed["image_path"] == "D:/data/teach_sample.BMP"


def test_path_traversal_rejected():
    req = {
        "request_id": "REQ-000003",
        "cmd": "inspect",
        "image_path": "../sensitive_file.png",
        "roi_mode": "AutoFrame",
        "param_source": "None",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg


def test_invalid_extension_rejected():
    req = {
        "request_id": "REQ-000004",
        "cmd": "inspect",
        "image_path": "C:/boot.ini",
        "roi_mode": "AutoFrame",
        "param_source": "None",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(json.dumps(req))
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported image extension" in exc_info.value.msg
