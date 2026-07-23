# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_parse_request_valid_extensions():
    for ext in (".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".BMP"):
        req = {
            "request_id": "REQ-000001",
            "cmd": "inspect",
            "image_path": f"image{ext}",
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        res = parse_request(json_to_line(req))
        assert res["image_path"] == f"image{ext}"


def test_parse_request_invalid_extensions():
    for ext in (".txt", ".json", ".exe", "", ".bin", ".png2"):
        req = {
            "request_id": "REQ-000001",
            "cmd": "inspect",
            "image_path": f"image{ext}",
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        with pytest.raises(ProtocolError) as excinfo:
            parse_request(json_to_line(req))
        assert excinfo.value.code == E_BAD_FIELD
        assert "invalid image file extension" in excinfo.value.msg


def test_parse_request_valid_paths():
    valid_paths = (
        "image.png",
        "subfolder/image.png",
        "/absolute/path/to/image.png",
        "C:\\absolute\\path\\to\\image.png",
        "C:/absolute/path/to/image.png",
        "image_.._test.png",  # double dots inside a name, not as a path segment
    )
    for p in valid_paths:
        req = {
            "request_id": "REQ-000001",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        res = parse_request(json_to_line(req))
        assert res["image_path"] == p


def test_parse_request_directory_traversal():
    invalid_paths = (
        "../image.png",
        "sub/../image.png",
        "sub/..\\image.png",
        "sub\\..\\image.png",
        "C:\\..\\image.png",
        "C:/../image.png",
        "image.png/..",
    )
    for p in invalid_paths:
        req = {
            "request_id": "REQ-000001",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        with pytest.raises(ProtocolError) as excinfo:
            parse_request(json_to_line(req))
        assert excinfo.value.code == E_BAD_FIELD
        assert "directory traversal detected" in excinfo.value.msg


def json_to_line(d: dict) -> str:
    import json
    return json.dumps(d)
