# -*- coding: utf-8 -*-
"""協定層資安驗證單元測試：驗證 image_path 的目錄穿越阻擋與副檔名白名單過濾。"""
import pytest

from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_parse_request_valid_image_paths():
    valid_paths = [
        "C:/images/test.png",
        "D:/data/sample.BMP",
        "/var/data/image.jpg",
        "relative/path/to/img.jpeg",
        "sample.tif",
        "sample.tiff",
    ]
    for path in valid_paths:
        req_str = (
            '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "%s"}'
            % path
        )
        parsed = parse_request(req_str)
        assert parsed["image_path"] == path


def test_parse_request_rejects_path_traversal():
    traversal_paths = [
        "../etc/passwd.png",
        "C:/images/../config.bmp",
        "foo/bar/../../secret.jpg",
    ]
    for path in traversal_paths:
        req_str = (
            '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "%s"}'
            % path
        )
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal" in exc_info.value.msg


def test_parse_request_rejects_invalid_file_extensions():
    invalid_paths = [
        "C:/images/script.py",
        "D:/data/config.json",
        "test.exe",
        "image.png.txt",
        "noextension",
    ]
    for path in invalid_paths:
        req_str = (
            '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "%s"}'
            % path
        )
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_str)
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in exc_info.value.msg
