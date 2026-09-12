# -*- coding: utf-8 -*-
"""通訊協定資安防護測試。

對 ve_server.protocol.parse_request 進行輸入驗證與資安邊界測試：
1. 合法圖片副檔名允許解析
2. 路徑穿越序列 (..) 拒絕解析
3. 非法/非圖片副檔名拒絕解析
"""
import json
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_valid_image_paths():
    valid_paths = [
        "image.png",
        "sample.JPG",
        "folder/test.bmp",
        "C:/images/panel_001.jpeg",
        "d:/data/scan.tif",
        "test.TIFF",
    ]
    for path in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-001",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == path


def test_path_traversal_rejected():
    traversal_paths = [
        "../etc/passwd.png",
        "../../config.json",
        "C:/images/../secret.png",
        "relative/../path.jpg",
    ]
    for path in traversal_paths:
        req_json = json.dumps({
            "request_id": "REQ-002",
            "cmd": "inspect",
            "image_path": path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_invalid_file_extension_rejected():
    invalid_paths = [
        "script.py",
        "data.txt",
        "executable.exe",
        "no_extension",
        "image.png.txt",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-003",
            "cmd": "teach",
            "image_path": path,
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image file extension" in exc_info.value.msg
