# -*- coding: utf-8 -*-
"""協定安全測試：驗證 image_path 的目錄穿越防禦與副檔名限制。"""
import pytest

import ve_server.protocol as P


def _make_req(cmd="inspect", image_path="valid.png", **kwargs):
    req = {
        "request_id": "REQ-TEST-001",
        "cmd": cmd,
        "image_path": image_path,
        "piece_id": "P001",
        "recipe_name": "RECIPE_A",
        "roi_mode": "AutoFrame",
    }
    if cmd == "inspect":
        req["param_source"] = "None"
    req.update(kwargs)
    import json
    return json.dumps(req)


def test_valid_image_paths():
    valid_paths = [
        "image.png",
        "testdata/real/1_cor.png",
        "C:\\Images\\photo.JPG",
        "D:/VisionWork/sample.bmp",
        "sample.TIFF",
    ]
    for p in valid_paths:
        parsed = P.parse_request(_make_req(cmd="inspect", image_path=p))
        assert parsed["image_path"] == p

        parsed_teach = P.parse_request(_make_req(cmd="teach", image_path=p))
        assert parsed_teach["image_path"] == p


def test_path_traversal_rejected():
    traversal_paths = [
        "../etc/passwd.png",
        "images/../secret.png",
        "C:\\Users\\..\\secret.jpg",
        "C:../secret.png",
        "C:..\\secret.png",
        "..",
        "a/b/../../secret.png",
    ]
    for p in traversal_paths:
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(_make_req(cmd="inspect", image_path=p))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg.lower()


def test_invalid_extension_rejected():
    invalid_ext_paths = [
        "file.txt",
        "config.json",
        "script.py",
        "image.png.exe",
        "no_ext",
    ]
    for p in invalid_ext_paths:
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(_make_req(cmd="inspect", image_path=p))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "unsupported image extension" in exc_info.value.msg.lower()
