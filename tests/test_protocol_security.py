# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD

def test_parse_request_valid():
    # Valid inspect request with valid extension and path
    req_str = '{"request_id": "REQ-01", "cmd": "inspect", "image_path": "C:/images/pic.png", "roi_mode": "AutoFrame"}'
    req = parse_request(req_str)
    assert req["image_path"] == "C:/images/pic.png"

    # Valid teach request with valid extension and path
    req_str = '{"request_id": "REQ-02", "cmd": "teach", "image_path": "/var/data/image.bmp"}'
    req = parse_request(req_str)
    assert req["image_path"] == "/var/data/image.bmp"

def test_parse_request_invalid_extensions():
    # Extension that is invalid (txt)
    req_str = '{"request_id": "REQ-01", "cmd": "inspect", "image_path": "C:/images/pic.txt", "roi_mode": "AutoFrame"}'
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(req_str)
    assert excinfo.value.code == E_BAD_FIELD
    assert "invalid file extension" in excinfo.value.msg

    # No extension at all
    req_str = '{"request_id": "REQ-01", "cmd": "inspect", "image_path": "C:/images/pic_no_ext", "roi_mode": "AutoFrame"}'
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(req_str)
    assert excinfo.value.code == E_BAD_FIELD
    assert "invalid file extension" in excinfo.value.msg

    # Invalid extension for teach
    req_str = '{"request_id": "REQ-02", "cmd": "teach", "image_path": "C:/images/pic.exe"}'
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(req_str)
    assert excinfo.value.code == E_BAD_FIELD

def test_parse_request_directory_traversal():
    # Relative path traversal
    req_str = '{"request_id": "REQ-01", "cmd": "inspect", "image_path": "../pic.png", "roi_mode": "AutoFrame"}'
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(req_str)
    assert excinfo.value.code == E_BAD_FIELD
    assert "directory traversal" in excinfo.value.msg

    # Traversal in the middle of path
    req_str = '{"request_id": "REQ-01", "cmd": "inspect", "image_path": "C:/images/../pic.png", "roi_mode": "AutoFrame"}'
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(req_str)
    assert excinfo.value.code == E_BAD_FIELD
    assert "directory traversal" in excinfo.value.msg

    # Backslash traversal
    req_str = '{"request_id": "REQ-01", "cmd": "inspect", "image_path": "C:\\\\images\\\\..\\\\pic.png", "roi_mode": "AutoFrame"}'
    with pytest.raises(ProtocolError) as excinfo:
        parse_request(req_str)
    assert excinfo.value.code == E_BAD_FIELD
    assert "directory traversal" in excinfo.value.msg
