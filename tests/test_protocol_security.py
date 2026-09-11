# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_parse_request_path_traversal_rejected():
    raw = json.dumps({
        "request_id": "REQ-000001",
        "cmd": "inspect",
        "image_path": "../secret/config.json",
        "piece_id": "P001",
        "recipe_name": "R001",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(raw)
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg


def test_parse_request_invalid_extension_rejected():
    raw = json.dumps({
        "request_id": "REQ-000002",
        "cmd": "teach",
        "image_path": "C:/images/payload.exe",
        "recipe_name": "R001",
        "roi_mode": "AutoFrame"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(raw)
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported image extension" in exc_info.value.msg


def test_parse_request_valid_image_path_allowed():
    raw = json.dumps({
        "request_id": "REQ-000003",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/sample.PNG",
        "piece_id": "P001",
        "recipe_name": "R001",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    })
    req = parse_request(raw)
    assert req["image_path"] == "D:/VisionWork/sample.PNG"
