# -*- coding: utf-8 -*-
"""協定安全單元測試：驗證路徑穿越防禦與影像副檔名白名單。"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def _make_req(cmd="inspect", image_path="C:/images/test.png", **extra):
    req = {
        "request_id": "REQ-000001",
        "cmd": cmd,
        "image_path": image_path,
        "roi_mode": "AutoFrame",
    }
    req.update(extra)
    return json.dumps(req)


def test_valid_image_extensions_pass():
    valid_exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".BMP", ".JPG"]
    for ext in valid_exts:
        line = _make_req(image_path="D:/data/sample" + ext)
        parsed = parse_request(line)
        assert parsed["image_path"] == "D:/data/sample" + ext


def test_path_traversal_rejected():
    traversal_paths = [
        "../etc/passwd",
        "C:/images/../secret.png",
        "..\\windows\\system32\\cmd.exe",
        "foo/bar/../../baz.jpg",
    ]
    for path in traversal_paths:
        line = _make_req(image_path=path)
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(line)
        assert exc_info.value.code == E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg.lower()


def test_invalid_extensions_rejected():
    invalid_paths = [
        "C:/images/test.txt",
        "D:/data/script.py",
        "E:/payload.exe",
        "C:/config.json",
        "D:/image.png.txt",
    ]
    for path in invalid_paths:
        line = _make_req(image_path=path)
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(line)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg.lower()
