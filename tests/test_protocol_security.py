# -*- coding: utf-8 -*-
"""協定安全層單元測試：路徑穿越防禦與影像副檔名白名單驗證。"""
import pytest
from ve_server.protocol import E_BAD_FIELD, ProtocolError, parse_request


def test_image_path_valid_extensions():
    valid_exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]
    for ext in valid_exts:
        req_json = (
            '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "images/test%s"}'
            % ext
        )
        req = parse_request(req_json)
        assert req["image_path"] == "images/test%s" % ext

        teach_json = (
            '{"request_id": "REQ-002", "cmd": "teach", "image_path": "images/teach%s"}'
            % ext
        )
        teach_req = parse_request(teach_json)
        assert teach_req["image_path"] == "images/teach%s" % ext


def test_image_path_invalid_extensions():
    invalid_paths = [
        "images/script.py",
        "images/malware.exe",
        "images/data.txt",
        "images/no_extension",
        "images/pic.png.exe",
    ]
    for p in invalid_paths:
        req_json = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "%s"}' % p
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "unsupported image extension" in exc_info.value.msg


def test_image_path_directory_traversal():
    traversal_paths = [
        "../etc/passwd.png",
        "C:/Windows/../System32/cmd.bmp",
        "foo/bar/../../secret.jpg",
        "..",
    ]
    for p in traversal_paths:
        req_json = '{"request_id": "REQ-001", "cmd": "inspect", "image_path": "%s"}' % p
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(req_json)
        assert exc_info.value.code == E_BAD_FIELD
        assert "directory traversal sequence" in exc_info.value.msg
