# -*- coding: utf-8 -*-
"""通訊協定安全與輸入校驗測試。

驗證 ve_server.protocol.parse_request 對於影像副檔名白名單、
路徑遍歷（..）、非 ASCII 內容及各項欄位界限的安全防護。
"""
import json
import pytest

from ve_server import protocol as P


def test_parse_request_valid_image_extensions():
    for ext in (".png", ".BMP", ".jpg", ".JPEG", ".tif", ".TIFF"):
        req_json = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": "C:/images/test_image" + ext,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        parsed = P.parse_request(req_json)
        assert parsed["cmd"] == "inspect"
        assert parsed["image_path"].lower().endswith(ext.lower())


def test_parse_request_invalid_image_extension_rejected():
    for invalid_path in ("C:/images/script.py", "C:/images/config.json", "C:/images/noext"):
        req_json = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": invalid_path,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(req_json)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg


def test_parse_request_path_traversal_rejected():
    traversal_paths = [
        "../secret.png",
        "C:/images/../../windows/system32/cmd.png",
        "dir/../image.png"
    ]
    for path in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-003",
            "cmd": "teach",
            "image_path": path,
            "roi_mode": "AutoFrame"
        })
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(req_json)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "path traversal sequence" in exc_info.value.msg


def test_parse_request_non_ascii_rejected():
    req_json = json.dumps({
        "request_id": "REQ-004",
        "cmd": "inspect",
        "image_path": "C:/images/測試.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    })
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(req_json)
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "non-ASCII" in exc_info.value.msg
