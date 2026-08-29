# -*- coding: utf-8 -*-
import json
import pytest

from ve_server import protocol as P


def test_valid_image_path():
    req_json = json.dumps({
        "request_id": "REQ-100",
        "cmd": "inspect",
        "image_path": "C:/images/sample.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    })
    parsed = P.parse_request(req_json)
    assert parsed["image_path"] == "C:/images/sample.png"


def test_path_traversal_rejected():
    req_json = json.dumps({
        "request_id": "REQ-101",
        "cmd": "inspect",
        "image_path": "../etc/passwd.png",
        "roi_mode": "AutoFrame"
    })
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(req_json)
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg


def test_invalid_extension_rejected():
    req_json = json.dumps({
        "request_id": "REQ-102",
        "cmd": "inspect",
        "image_path": "C:/images/secret.txt",
        "roi_mode": "AutoFrame"
    })
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(req_json)
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "unsupported image extension" in exc_info.value.msg


def test_no_extension_rejected():
    req_json = json.dumps({
        "request_id": "REQ-103",
        "cmd": "teach",
        "image_path": "C:/images/sample_no_ext",
        "roi_mode": "AutoFrame"
    })
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(req_json)
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "unsupported image extension" in exc_info.value.msg
