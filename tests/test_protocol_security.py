# -*- coding: utf-8 -*-
"""協定層安全性驗證測試：路徑穿透、副檔名過濾、非 ASCII 檢查等。"""

import pytest
from ve_server.protocol import (
    E_BAD_FIELD,
    E_UNKNOWN_CMD,
    ProtocolError,
    parse_request,
)


def test_protocol_image_path_security():
    # Valid request
    valid_req = {
        "request_id": "REQ-0001",
        "cmd": "inspect",
        "image_path": "D:/images/sample.png",
        "roi_mode": "AutoFrame",
    }
    parsed = parse_request(str(valid_req).replace("'", '"'))
    assert parsed["image_path"] == "D:/images/sample.png"

    # Directory traversal rejection
    traversal_req = {
        "request_id": "REQ-0002",
        "cmd": "inspect",
        "image_path": "../../etc/passwd.png",
        "roi_mode": "AutoFrame",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(str(traversal_req).replace("'", '"'))
    assert exc_info.value.code == E_BAD_FIELD
    assert "directory traversal" in exc_info.value.msg

    # Invalid extension rejection
    invalid_ext_req = {
        "request_id": "REQ-0003",
        "cmd": "inspect",
        "image_path": "D:/images/malicious.exe",
        "roi_mode": "AutoFrame",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(str(invalid_ext_req).replace("'", '"'))
    assert exc_info.value.code == E_BAD_FIELD
    assert "extension" in exc_info.value.msg


def test_protocol_allowed_extensions():
    for ext in [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"]:
        req = {
            "request_id": "REQ-EXT",
            "cmd": "teach",
            "image_path": f"C:/test/image{ext}",
            "roi_mode": "AutoFrame",
        }
        parsed = parse_request(str(req).replace("'", '"'))
        assert parsed["cmd"] == "teach"


def test_protocol_non_ascii_rejection():
    req = {
        "request_id": "REQ-ASCII",
        "cmd": "inspect",
        "image_path": "D:/影像/test.png",
        "roi_mode": "AutoFrame",
    }
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(str(req).replace("'", '"'))
    assert exc_info.value.code == E_BAD_FIELD
    assert "non-ASCII" in exc_info.value.msg
