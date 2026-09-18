# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_protocol_path_traversal_rejection():
    # Attempt directory traversal via image_path in inspect and teach
    for path in ["../secret.png", "c:\\foo\\..\\bar.bmp", "test/../../etc/passwd.jpg"]:
        req_inspect = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_inspect)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg

        req_teach = json.dumps({
            "request_id": "req-2",
            "cmd": "teach",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_teach)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_protocol_unsupported_file_extensions():
    # Non-image extensions should be rejected
    for path in ["config.json", "script.py", "executable.exe", "file.txt", "image.pdf"]:
        req = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported file extension" in exc_info.value.msg


def test_protocol_valid_image_extensions():
    # Valid image extensions (case insensitive) should be accepted
    valid_paths = [
        "images/test1.png",
        "images/test2.BMP",
        "images/test3.jpg",
        "images/test4.JPEG",
        "images/test5.tif",
        "images/test6.TIFF",
    ]
    for path in valid_paths:
        req = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": path
        })
        parsed = parse_request(req)
        assert parsed["image_path"] == path
