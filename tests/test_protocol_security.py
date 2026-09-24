# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import (
    E_BAD_FIELD,
    ProtocolError,
    parse_request,
)


def test_parse_request_valid_image_paths():
    for ext in (".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG"):
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": f"C:/images/test{ext}",
            "piece_id": "P001",
            "recipe_name": "R1",
        })
        req = parse_request(req_json)
        assert req["image_path"] == f"C:/images/test{ext}"


def test_parse_request_path_traversal_rejected():
    bad_paths = [
        "../etc/passwd.png",
        "C:/images/../secret.png",
        "..\\windows\\system32\\cmd.exe.png",
        "foo/bar/../../baz.jpg",
    ]
    for bad_path in bad_paths:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": bad_path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_parse_request_invalid_extension_rejected():
    bad_extensions = [
        "C:/images/test.txt",
        "C:/images/test.exe",
        "C:/images/test.py",
        "C:/images/test.png.txt",
        "C:/images/test",
    ]
    for bad_path in bad_extensions:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": bad_path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path file extension" in exc_info.value.msg


def test_parse_request_non_ascii_rejected():
    req_json = json.dumps({
        "request_id": "REQ-0001",
        "cmd": "inspect",
        "image_path": "C:/images/測試.png",
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "contains non-ASCII" in exc_info.value.msg
