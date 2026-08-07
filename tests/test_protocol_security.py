# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_valid_image_paths():
    # 測試合法路徑與支援的副檔名（大小寫皆可）
    valid_paths = [
        "image.png",
        "image.PNG",
        "D:/VisionWork/image_001.jpg",
        "C:\\images\\test.jpeg",
        "sample.bmp",
        "pic.tif",
        "another.tiff",
    ]
    for path in valid_paths:
        req_json = json.dumps({
            "request_id": "REQ-12345",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        })
        parsed = parse_request(req_json)
        assert parsed["image_path"] == path

def test_directory_traversal_rejected():
    # 測試路徑穿越（Path Traversal）安全防禦
    invalid_paths = [
        "../image.png",
        "..\\image.png",
        "C:/work/../image.png",
        "C:\\work\\..\\image.png",
        "/usr/local/../bin/image.png",
        "image..png", # This is fine for ext split, but contains '..' so it should be rejected as traversal security policy
    ]
    for path in invalid_paths:
        req_json = json.dumps({
            "request_id": "REQ-12345",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg

def test_unsupported_extensions_rejected():
    # 測試不支援的副檔名
    invalid_exts = [
        "image.txt",
        "image.png.exe",
        "image.pdf",
        "image",
        "image.gif",
        ".bashrc",
    ]
    for path in invalid_exts:
        req_json = json.dumps({
            "request_id": "REQ-12345",
            "cmd": "inspect",
            "image_path": path,
            "roi_mode": "AutoFrame"
        })
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image format" in exc_info.value.msg
