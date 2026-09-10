# -*- coding: utf-8 -*-
"""安全檢測單元測試：驗證協定解析層（ve_server/protocol.py）對 image_path 的安全性檢查。"""

import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_parse_request_valid_image_path():
    """正常 valid 圖片路徑與副檔名應順利解析。"""
    raw = json.dumps({
        "request_id": "req-001",
        "cmd": "inspect",
        "image_path": "C:/images/sample.png",
    })
    req = parse_request(raw)
    assert req["image_path"] == "C:/images/sample.png"


@pytest.mark.parametrize("ext", [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"])
def test_parse_request_valid_extensions(ext):
    """所有支援的副檔名皆應通過驗證。"""
    raw = json.dumps({
        "request_id": "req-002",
        "cmd": "teach",
        "image_path": f"test{ext}",
    })
    req = parse_request(raw)
    assert req["image_path"] == f"test{ext}"


@pytest.mark.parametrize("bad_path", [
    "../secret.png",
    "..\\secret.png",
    "foo/../../bar.jpg",
    "C:/data/../config.bmp",
])
def test_parse_request_path_traversal_rejected(bad_path):
    """包含路徑穿越序列 (..) 的請求應被拒絕並丟出 E_BAD_FIELD 的 ProtocolError。"""
    raw = json.dumps({
        "request_id": "req-003",
        "cmd": "inspect",
        "image_path": bad_path,
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(raw)
    assert exc_info.value.code == E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg.lower()


@pytest.mark.parametrize("unsupported_ext", [
    "image.exe",
    "script.sh",
    "document.pdf",
    "data.json",
    "image.png.exe",
])
def test_parse_request_unsupported_extension_rejected(unsupported_ext):
    """非支援之副檔名請求應被拒絕並丟出 E_BAD_FIELD 的 ProtocolError。"""
    raw = json.dumps({
        "request_id": "req-004",
        "cmd": "inspect",
        "image_path": unsupported_ext,
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(raw)
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported file extension" in exc_info.value.msg.lower()
