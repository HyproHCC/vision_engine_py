# -*- coding: utf-8 -*-
"""protocol Security Tests: Path Traversal & File Extension Validation."""
import json
import pytest

from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_valid_image_path_extensions():
    valid_paths = [
        "C:/images/test.png",
        "C:/images/test.PNG",
        "/var/data/sample.bmp",
        "sample.jpg",
        "sample.JPEG",
        "sample.tif",
        "sample.TIFF",
    ]
    for path in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": path
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == path


def test_path_traversal_rejected():
    invalid_paths = [
        "../etc/passwd.png",
        "C:/images/../../secret.jpg",
        "..\\windows\\system32\\cmd.png",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_disallowed_extensions_rejected():
    invalid_paths = [
        "C:/images/script.py",
        "C:/images/config.json",
        "C:/images/exec.exe",
        "C:/images/no_extension",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-1",
            "cmd": "inspect",
            "image_path": path
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg


def test_teach_command_security_validation():
    # Path traversal in teach
    req_json = json.dumps({
        "request_id": "REQ-2",
        "cmd": "teach",
        "image_path": "../../teach.png"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD

    # Disallowed extension in teach
    req_json = json.dumps({
        "request_id": "REQ-2",
        "cmd": "teach",
        "image_path": "teach.sh"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
