# -*- coding: utf-8 -*-
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_protocol_security_valid_image_path():
    req = {
        "request_id": "REQ-101",
        "cmd": "inspect",
        "image_path": "C:/VisionData/sample_01.png"
    }
    parsed = parse_request(json.dumps(req))
    assert parsed["image_path"] == "C:/VisionData/sample_01.png"


def test_protocol_security_valid_extensions():
    for ext in [".png", ".PNG", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"]:
        req = {
            "request_id": "REQ-102",
            "cmd": "teach",
            "image_path": f"C:/VisionData/sample{ext}"
        }
        parsed = parse_request(json.dumps(req))
        assert parsed["image_path"].endswith(ext)


def test_protocol_security_invalid_extension():
    for invalid_path in [
        "C:/VisionData/sample.txt",
        "C:/VisionData/config.json",
        "C:/VisionData/script.py",
        "C:/VisionData/sample.exe"
    ]:
        req = {
            "request_id": "REQ-103",
            "cmd": "inspect",
            "image_path": invalid_path
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg


def test_protocol_security_path_traversal():
    for traversal_path in [
        "../etc/passwd.png",
        "C:/VisionData/../secret.png",
        "..\\windows\\system32\\cmd.jpg",
        "sub/../../test.bmp"
    ]:
        req = {
            "request_id": "REQ-104",
            "cmd": "inspect",
            "image_path": traversal_path
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req))
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg
