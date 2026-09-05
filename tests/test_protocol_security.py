# -*- coding: utf-8 -*-
import json
import pytest

from ve_server import protocol as P


def test_valid_image_path_extensions():
    for ext in (".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG"):
        req_str = json.dumps({
            "request_id": "req-1",
            "cmd": "inspect",
            "image_path": f"C:/images/test{ext}"
        })
        parsed = P.parse_request(req_str)
        assert parsed["image_path"] == f"C:/images/test{ext}"


def test_path_traversal_rejected():
    invalid_paths = [
        "../etc/passwd.png",
        "C:/images/../secret.png",
        "sub/../../test.png",
        "..\\windows\\system32\\test.png",
    ]
    for path in invalid_paths:
        req_str = json.dumps({
            "request_id": "req-2",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(req_str)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_disallowed_file_extensions():
    invalid_paths = [
        "C:/images/script.py",
        "C:/images/malware.exe",
        "C:/images/config.json",
        "C:/images/no_extension",
    ]
    for path in invalid_paths:
        req_str = json.dumps({
            "request_id": "req-3",
            "cmd": "teach",
            "image_path": path
        })
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(req_str)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "extension not allowed" in exc_info.value.msg
