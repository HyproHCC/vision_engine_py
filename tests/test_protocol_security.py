# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_protocol_security_path_traversal():
    # 測試帶有 .. 的路徑
    req_json = json.dumps({
        "request_id": "REQ-000001",
        "cmd": "inspect",
        "image_path": "../../../etc/passwd.png"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info.value.msg


def test_protocol_security_invalid_extension():
    # 測試不合法的副檔名
    req_json = json.dumps({
        "request_id": "REQ-000002",
        "cmd": "inspect",
        "image_path": "test.txt"
    })
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(req_json)
    assert exc_info.value.code == E_BAD_FIELD
    assert "extension not allowed" in exc_info.value.msg


def test_protocol_security_valid_image_path():
    # 測試合法副檔名與正常路徑
    for ext in [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG"]:
        req_json = json.dumps({
            "request_id": "REQ-000003",
            "cmd": "inspect",
            "image_path": f"C:/images/sample{ext}"
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == f"C:/images/sample{ext}"
