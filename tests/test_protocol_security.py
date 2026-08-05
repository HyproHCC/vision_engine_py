# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_ping_protocol_parsing():
    # Ping should parse perfectly as it doesn't check image_path
    req = parse_request('{"request_id": "REQ-01", "cmd": "ping"}')
    assert req["cmd"] == "ping"
    assert req["request_id"] == "REQ-01"


def test_valid_image_paths():
    # Valid extensions should pass
    for ext in (".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".Bmp", ".JPEG"):
        payload = {
            "request_id": "REQ-02",
            "cmd": "inspect",
            "image_path": f"/path/to/image{ext}",
            "roi_mode": "AutoFrame"
        }
        import json
        req = parse_request(json.dumps(payload))
        assert req["image_path"] == f"/path/to/image{ext}"


def test_path_traversal_rejection():
    # Path traversal patterns should be rejected
    traversal_paths = [
        "../test.png",
        "some/path/../test.png",
        "..\\test.png",
        "some\\path\\..\\test.png",
        "C:/foo/bar/../../test.png",
    ]
    for path in traversal_paths:
        payload = {
            "request_id": "REQ-03",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        }
        import json
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(payload))
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_invalid_file_extension_rejection():
    # Invalid extensions or missing extensions should be rejected
    bad_paths = [
        "/path/to/image.txt",
        "/path/to/image.json",
        "/path/to/image",
        "/path/to/image.png.txt",
    ]
    for path in bad_paths:
        payload = {
            "request_id": "REQ-04",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        }
        import json
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(payload))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path file extension" in exc_info.value.msg
