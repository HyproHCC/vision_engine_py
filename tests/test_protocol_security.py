# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_valid_request_passes():
    req_json = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "C:/images/test.png"}'
    parsed = parse_request(req_json)
    assert parsed["cmd"] == "inspect"
    assert parsed["image_path"] == "C:/images/test.png"


def test_missing_image_path():
    req_json = '{"request_id": "REQ-001", "cmd": "inspect"}'
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "missing image_path" in exc_info.value.msg


def test_directory_traversal_rejected():
    traversal_paths = [
        "../etc/passwd.png",
        "C:/images/../secret.png",
        "foo/../../bar.jpg",
    ]
    for p in traversal_paths:
        req_json = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "%s"}' % p
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_invalid_extension_rejected():
    invalid_paths = [
        "C:/images/test.exe",
        "C:/images/test.txt",
        "C:/images/test.py",
        "C:/images/test",
    ]
    for p in invalid_paths:
        req_json = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "%s"}' % p
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "extension" in exc_info.value.msg


def test_allowed_extensions_accepted():
    allowed_paths = [
        "C:/images/test.png",
        "C:/images/test.PNG",
        "C:/images/test.bmp",
        "C:/images/test.jpg",
        "C:/images/test.jpeg",
        "C:/images/test.tif",
        "C:/images/test.tiff",
    ]
    for p in allowed_paths:
        req_json = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "%s"}' % p
        parsed = parse_request(req_json)
        assert parsed["image_path"] == p


def test_non_ascii_rejected():
    req_json = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "C:/影像/test.png"}'
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "non-ASCII" in exc_info.value.msg
