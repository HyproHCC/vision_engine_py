# -*- coding: utf-8 -*-
"""protocol.py 安全性驗證測試：檔名副檔名白名單與路徑穿越防禦。"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def _make_req(cmd="inspect", image_path="C:/images/test.png", **kwargs):
    req = {
        "request_id": "REQ-000123",
        "cmd": cmd,
        "image_path": image_path,
        "roi_mode": "AutoFrame",
    }
    if cmd == "inspect":
        req["param_source"] = "None"
    req.update(kwargs)
    return json.dumps(req)


@pytest.mark.parametrize("cmd", ["inspect", "teach"])
@pytest.mark.parametrize("traversal_path", [
    "../secret.png",
    "../../etc/passwd.png",
    "C:/images/../config.png",
    "sub/dir/../../test.png",
])
def test_parse_request_rejects_path_traversal(cmd, traversal_path):
    raw = _make_req(cmd=cmd, image_path=traversal_path)
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(raw)
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info.value.msg


@pytest.mark.parametrize("cmd", ["inspect", "teach"])
@pytest.mark.parametrize("bad_ext_path", [
    "C:/images/script.py",
    "C:/images/executable.exe",
    "C:/images/notes.txt",
    "C:/images/no_extension",
    "C:/images/data.json",
])
def test_parse_request_rejects_unsupported_extensions(cmd, bad_ext_path):
    raw = _make_req(cmd=cmd, image_path=bad_ext_path)
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(raw)
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported image_path extension" in exc_info.value.msg


@pytest.mark.parametrize("cmd", ["inspect", "teach"])
@pytest.mark.parametrize("valid_path", [
    "C:/images/sample.png",
    "C:/images/sample.PNG",
    "C:/images/sample.bmp",
    "C:/images/sample.jpg",
    "C:/images/sample.jpeg",
    "C:/images/sample.tif",
    "C:/images/sample.tiff",
    "D:/VisionWork/img_20260706_101500_001.png",
])
def test_parse_request_accepts_valid_image_paths(cmd, valid_path):
    raw = _make_req(cmd=cmd, image_path=valid_path)
    parsed = parse_request(raw)
    assert parsed["image_path"] == valid_path
