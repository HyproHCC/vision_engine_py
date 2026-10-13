# -*- coding: utf-8 -*-
"""資安測試：驗證 ve_server/protocol.py 中的輸入驗證與防護邏輯。

1. image_path 目錄穿透 (Directory Traversal) 阻擋 (如 `..`)
2. image_path 副檔名白名單限制 (.png, .bmp, .jpg, .jpeg, .tif, .tiff)
"""
import json
import pytest

from ve_server import protocol as P


def test_valid_image_paths_pass_parsing():
    """驗證各類許可的影像格式副檔名皆能順利通過解析。"""
    valid_paths = [
        "D:/VisionWork/img_001.png",
        "D:/VisionWork/img_002.BMP",
        "C:/data/test.jpg",
        "relative/path/test.jpeg",
        "test.tif",
        "test.TIFF",
    ]
    for path in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0001",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        parsed = P.parse_request(req_json)
        assert parsed["image_path"] == path


def test_path_traversal_rejected():
    """驗證包含目錄穿透 (..) 序列的 image_path 會被阻擋。"""
    invalid_paths = [
        "../etc/passwd.png",
        "D:/VisionWork/../secret.png",
        "..\\windows\\system32\\cmd.jpg",
        "C:/Work/dir/../../test.png",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0002",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        })
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(req_json)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg.lower()


def test_unsupported_file_extensions_rejected():
    """驗證非許可副檔名（如 .txt, .exe, 無副檔名）會被阻擋。"""
    invalid_paths = [
        "D:/VisionWork/config.txt",
        "D:/VisionWork/payload.exe",
        "D:/VisionWork/image_no_ext",
        "D:/VisionWork/script.py",
        "D:/VisionWork/test.png.txt",
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-0003",
            "cmd": "teach",
            "image_path": path,
            "recipe_name": "TYPE_A",
            "roi_mode": "AutoFrame"
        })
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(req_json)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "unsupported file extension" in exc_info.value.msg.lower()


def test_missing_or_empty_image_path_rejected():
    """驗證缺少或空字串 image_path 會被阻擋。"""
    bad_reqs = [
        {"request_id": "REQ-0004", "cmd": "inspect", "image_path": ""},
        {"request_id": "REQ-0005", "cmd": "inspect", "image_path": None},
        {"request_id": "REQ-0006", "cmd": "inspect"},
    ]
    for req in bad_reqs:
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(json.dumps(req))
        assert exc_info.value.code == P.E_BAD_FIELD
