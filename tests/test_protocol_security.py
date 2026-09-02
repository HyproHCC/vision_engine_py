# -*- coding: utf-8 -*-
"""Protocol security tests: path traversal and file extension validation."""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def _make_req(cmd="inspect", image_path="valid_image.png", **kwargs):
    base = {
        "request_id": "REQ-000001",
        "cmd": cmd,
        "image_path": image_path,
        "recipe_name": "TYPE_A",
        "roi_mode": "AutoFrame",
    }
    if cmd == "inspect":
        base["piece_id"] = "PIECE-001"
        base["param_source"] = "None"
    base.update(kwargs)
    return json.dumps(base)


def test_valid_image_extensions():
    valid_paths = [
        "sample.png",
        "SAMPLE.PNG",
        "folder/image.jpg",
        "C:/images/test.jpeg",
        "test.bmp",
        "image.tif",
        "image.tiff",
    ]
    for p in valid_paths:
        req_str = _make_req(cmd="inspect", image_path=p)
        parsed = parse_request(req_str)
        assert parsed["image_path"] == p

        req_str_teach = _make_req(cmd="teach", image_path=p)
        parsed_teach = parse_request(req_str_teach)
        assert parsed_teach["image_path"] == p


def test_directory_traversal_rejection():
    traversal_paths = [
        "../etc/passwd",
        "C:/data/../secret.png",
        "images/../../config.json",
        "..\\windows\\system32\\cmd.exe.png",
    ]
    for p in traversal_paths:
        req_str = _make_req(cmd="inspect", image_path=p)
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_disallowed_file_extensions():
    invalid_paths = [
        "executable.exe",
        "script.py",
        "data.txt",
        "config.json",
        "noextension",
        "fake.png.exe",
    ]
    for p in invalid_paths:
        req_str = _make_req(cmd="inspect", image_path=p)
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "extension" in exc_info.value.msg
