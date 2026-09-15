# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import (
    E_BAD_FIELD,
    ProtocolError,
    parse_request,
)


def test_valid_image_path_extensions():
    valid_paths = [
        "C:/images/sample.png",
        "D:/work/test.bmp",
        "E:/data/photo.jpg",
        "F:/data/photo.jpeg",
        "G:/data/image.tif",
        "H:/data/image.tiff",
        "IMAGE.PNG",
    ]
    for p in valid_paths:
        req_str = json.dumps({
            "request_id": "REQ-000001",
            "cmd": "inspect",
            "image_path": p,
            "recipe_name": "TYPE_A",
        })
        parsed = parse_request(req_str)
        assert parsed["image_path"] == p


def test_image_path_traversal_rejected():
    invalid_paths = [
        "../secret.png",
        "C:/images/../secret.png",
        "../../etc/passwd",
        "foo/bar/../baz.bmp",
    ]
    for p in invalid_paths:
        req_str = json.dumps({
            "request_id": "REQ-000002",
            "cmd": "inspect",
            "image_path": p,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_unsupported_image_path_extension_rejected():
    invalid_ext_paths = [
        "C:/images/script.sh",
        "D:/work/executable.exe",
        "E:/data/notes.txt",
        "F:/data/config.json",
        "G:/data/source.py",
        "H:/data/noextension",
    ]
    for p in invalid_ext_paths:
        req_str = json.dumps({
            "request_id": "REQ-000003",
            "cmd": "teach",
            "image_path": p,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image_path extension" in exc_info.value.msg


def test_non_ascii_image_path_rejected():
    req_str = json.dumps({
        "request_id": "REQ-000004",
        "cmd": "inspect",
        "image_path": "C:/圖片/test.png",
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_str)
    assert exc_info.value.code == E_BAD_FIELD
    assert "contains non-ASCII" in exc_info.value.msg
