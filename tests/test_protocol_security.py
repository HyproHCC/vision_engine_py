# -*- coding: utf-8 -*-
"""協定安全驗證單元測試（ve_server/protocol.py）。"""
import json
import pytest
from ve_server import protocol as P


def test_valid_image_paths():
    """驗證合法圖像副檔名皆可正常通過驗證。"""
    valid_exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]
    for ext in valid_exts:
        req = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": "test%s" % ext,
            "param_source": "None",
        }
        parsed = P.parse_request(json.dumps(req))
        assert parsed["image_path"] == "test%s" % ext


def test_path_traversal_rejected():
    """驗證包含 '..' 之路徑穿透請求會被拒絕。"""
    traversal_paths = [
        "../secret.png",
        "images/../../etc/passwd.png",
        "..\\windows\\system32\\cmd.png",
    ]
    for path in traversal_paths:
        req = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
            "param_source": "None",
        }
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(json.dumps(req))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_invalid_extension_rejected():
    """驗證不合規副檔名請求會被拒絕。"""
    invalid_paths = [
        "file.txt",
        "script.py",
        "config.json",
        "malware.exe",
        "image.png.txt",
    ]
    for path in invalid_paths:
        req = {
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
            "param_source": "None",
        }
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(json.dumps(req))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg
