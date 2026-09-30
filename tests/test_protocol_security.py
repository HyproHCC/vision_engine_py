# -*- coding: utf-8 -*-
"""Protocol 安全驗證單元測試。"""

import json
import pytest

from ve_server import protocol as P


def test_protocol_security_path_traversal():
    """驗證包含路徑穿越 (..) 的 image_path 會被拒絕。"""
    req_data = {
        "request_id": "REQ-SEC-001",
        "cmd": "inspect",
        "image_path": "../etc/passwd",
        "param_source": "None"
    }
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(json.dumps(req_data))
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "path traversal" in exc_info.value.msg


def test_protocol_security_disallowed_extension():
    """驗證非允許之影像副檔名會被拒絕。"""
    invalid_paths = [
        "test.txt",
        "script.py",
        "malicious.exe",
        "data.json",
        "image_no_ext"
    ]
    for p in invalid_paths:
        req_data = {
            "request_id": "REQ-SEC-002",
            "cmd": "inspect",
            "image_path": p,
            "param_source": "None"
        }
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(json.dumps(req_data))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg


def test_protocol_security_allowed_extensions():
    """驗證合法影像副檔名（大小寫皆可）能順利通過驗證。"""
    valid_paths = [
        "C:/images/sample.png",
        "sample2.PNG",
        "/var/data/test.jpg",
        "test2.JPEG",
        "test3.bmp",
        "test4.tif",
        "test5.TIFF",
    ]
    for p in valid_paths:
        req_data = {
            "request_id": "REQ-SEC-003",
            "cmd": "inspect",
            "image_path": p,
            "param_source": "None"
        }
        parsed = P.parse_request(json.dumps(req_data))
        assert parsed["image_path"] == p


def test_protocol_security_non_ascii_field():
    """驗證 ASCII 欄位包含中文或其他非 ASCII 字元會被拒絕。"""
    req_data = {
        "request_id": "REQ-SEC-004",
        "cmd": "inspect",
        "image_path": "sample.png",
        "piece_id": "工件-001",
        "param_source": "None"
    }
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(json.dumps(req_data))
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "non-ASCII" in exc_info.value.msg


def test_protocol_security_invalid_manual_roi():
    """驗證 Manual ROI right <= left 或 bottom <= top 會被拒絕。"""
    req_data = {
        "request_id": "REQ-SEC-005",
        "cmd": "inspect",
        "image_path": "sample.png",
        "roi_mode": "Manual",
        "roi_rect": {"left": 100, "top": 100, "right": 50, "bottom": 200},
        "param_source": "None"
    }
    with pytest.raises(P.ProtocolError) as exc_info:
        P.parse_request(json.dumps(req_data))
    assert exc_info.value.code == P.E_BAD_FIELD
    assert "right>left and bottom>top" in exc_info.value.msg
