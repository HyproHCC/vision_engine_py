# -*- coding: utf-8 -*-
"""協定安全性單元測試：驗證路徑穿越、副檔名驗證、ASCII 限制與基礎通訊協定欄位驗證。"""
import json
import pytest

from ve_server.protocol import (
    E_BAD_FIELD,
    E_UNKNOWN_CMD,
    E_BAD_JSON,
    ProtocolError,
    parse_request,
)


def test_parse_request_valid_inspect():
    req_json = json.dumps({
        "request_id": "REQ-000001",
        "cmd": "inspect",
        "image_path": "C:/images/sample.png",
        "piece_id": "P001",
        "recipe_name": "TYPE_A",
        "roi_mode": "AutoFrame",
    })
    parsed = parse_request(req_json)
    assert parsed["request_id"] == "REQ-000001"
    assert parsed["cmd"] == "inspect"
    assert parsed["image_path"] == "C:/images/sample.png"


@pytest.mark.parametrize("ext", [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".BMP"])
def test_parse_request_valid_extensions(ext):
    req_json = json.dumps({
        "request_id": "REQ-000002",
        "cmd": "inspect",
        "image_path": f"D:/data/test_file{ext}",
    })
    parsed = parse_request(req_json)
    assert parsed["image_path"].lower().endswith(ext.lower())


@pytest.mark.parametrize("bad_path", [
    "../secret.png",
    "C:/images/../etc/passwd.png",
    "..\\windows\\system32\\cmd.png",
    "subfolder/../../test.png",
])
def test_parse_request_rejects_path_traversal(bad_path):
    req_json = json.dumps({
        "request_id": "REQ-000003",
        "cmd": "inspect",
        "image_path": bad_path,
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info.value.msg.lower()


@pytest.mark.parametrize("invalid_ext_path", [
    "C:/images/script.py",
    "C:/images/data.txt",
    "C:/images/malicious.exe",
    "C:/images/no_extension",
])
def test_parse_request_rejects_unsupported_extensions(invalid_ext_path):
    req_json = json.dumps({
        "request_id": "REQ-000004",
        "cmd": "inspect",
        "image_path": invalid_ext_path,
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "unsupported" in exc_info.value.msg.lower()


def test_parse_request_rejects_non_ascii_fields():
    req_json = json.dumps({
        "request_id": "REQ-000005",
        "cmd": "inspect",
        "image_path": "C:/images/影像.png",
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "non-ascii" in exc_info.value.msg.lower()


def test_parse_request_unknown_cmd():
    req_json = json.dumps({
        "request_id": "REQ-000006",
        "cmd": "eval",
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_UNKNOWN_CMD
