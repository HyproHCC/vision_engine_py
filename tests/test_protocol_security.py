# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_valid_image_path_extensions():
    valid_paths = [
        "C:/images/test.png",
        "D:\\data\\sample.BMP",
        "/var/data/image.jpg",
        "photo.jpeg",
        "scan.tif",
        "raw.tiff",
    ]
    for path in valid_paths:
        req_inspect = json.dumps({"request_id": "REQ-1", "cmd": "inspect", "image_path": path})
        parsed_inspect = parse_request(req_inspect)
        assert parsed_inspect["image_path"] == path

        req_teach = json.dumps({"request_id": "REQ-2", "cmd": "teach", "image_path": path})
        parsed_teach = parse_request(req_teach)
        assert parsed_teach["image_path"] == path


def test_reject_directory_traversal():
    traversal_paths = [
        "../secret.png",
        "C:/images/../config.json.png",  # contains '..'
        "..\\data\\test.bmp",
        "/etc/../var/image.jpg",
    ]
    for path in traversal_paths:
        req = json.dumps({"request_id": "REQ-1", "cmd": "inspect", "image_path": path})
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_reject_disallowed_extensions():
    invalid_paths = [
        "C:/config.json",
        "script.py",
        "executable.exe",
        "data.txt",
        "noextension",
        "image.png.bak",
    ]
    for path in invalid_paths:
        req = json.dumps({"request_id": "REQ-1", "cmd": "inspect", "image_path": path})
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid file extension" in exc_info.value.msg
