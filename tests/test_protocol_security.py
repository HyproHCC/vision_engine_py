# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD, E_OK, E_UNKNOWN_CMD


def test_parse_request_valid_image_paths():
    valid_paths = [
        "C:/images/test.png",
        "D:\\VisionWork\\sample.bmp",
        "/tmp/test_image.jpg",
        "relative/path/image.jpeg",
        "sample.tif",
        "sample.TIFF",
        "sample.PNG",
    ]
    for p in valid_paths:
        req_inspect = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": p,
        }
        parsed = parse_request(json.dumps(req_inspect))
        assert parsed["image_path"] == p

        req_teach = {
            "request_id": "REQ-002",
            "cmd": "teach",
            "image_path": p,
        }
        parsed_teach = parse_request(json.dumps(req_teach))
        assert parsed_teach["image_path"] == p


def test_parse_request_path_traversal_rejected():
    traversal_paths = [
        "../secret.png",
        "../../etc/passwd.png",
        "C:\\images\\..\\config.bmp",
        "foo/bar/../baz.jpg",
    ]
    for p in traversal_paths:
        req = {
            "request_id": "REQ-003",
            "cmd": "inspect",
            "image_path": p,
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_parse_request_invalid_extension_rejected():
    invalid_ext_paths = [
        "C:/images/test.txt",
        "D:\\VisionWork\\script.py",
        "/tmp/data.json",
        "exec.exe",
        "image.png.bak",
        "image_no_ext",
    ]
    for p in invalid_ext_paths:
        req = {
            "request_id": "REQ-004",
            "cmd": "inspect",
            "image_path": p,
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image_path extension" in exc_info.value.msg
