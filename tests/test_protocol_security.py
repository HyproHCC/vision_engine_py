# -*- coding: utf-8 -*-
import json
import pytest
from ve_server.protocol import parse_request, ProtocolError, E_BAD_FIELD


def test_protocol_security_image_path_allowed_extensions():
    # Valid extensions (case insensitive)
    valid_extensions = [".png", ".PNG", ".bmp", ".BMP", ".jpg", ".JPG", ".jpeg", ".JPEG", ".tif", ".TIF", ".tiff", ".TIFF"]
    for ext in valid_extensions:
        req_inspect = {
            "request_id": "REQ-123456",
            "cmd": "inspect",
            "image_path": f"D:/images/sample{ext}",
            "piece_id": "P001",
            "recipe_name": "RECIPE_A",
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        parsed = parse_request(json.dumps(req_inspect))
        assert parsed["image_path"] == f"D:/images/sample{ext}"

        req_teach = {
            "request_id": "REQ-123456",
            "cmd": "teach",
            "image_path": f"D:/images/sample{ext}",
            "recipe_name": "RECIPE_A",
            "roi_mode": "AutoFrame"
        }
        parsed = parse_request(json.dumps(req_teach))
        assert parsed["image_path"] == f"D:/images/sample{ext}"


def test_protocol_security_image_path_disallowed_extensions():
    # Disallowed extensions
    disallowed = [".txt", ".exe", ".py", ".json", ".ini", ".bat", "", "sample_no_ext"]
    for ext in disallowed:
        req_inspect = {
            "request_id": "REQ-123456",
            "cmd": "inspect",
            "image_path": f"D:/images/sample{ext}",
            "piece_id": "P001",
            "recipe_name": "RECIPE_A",
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req_inspect))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in str(exc_info.value)

        req_teach = {
            "request_id": "REQ-123456",
            "cmd": "teach",
            "image_path": f"D:/images/sample{ext}",
            "recipe_name": "RECIPE_A",
            "roi_mode": "AutoFrame"
        }
        with pytest.raises(ProtocolError) as exc_info:
            parse_request(json.dumps(req_teach))
        assert exc_info.value.code == E_BAD_FIELD
        assert "invalid image_path extension" in str(exc_info.value)


def test_protocol_security_other_cmds_not_affected():
    # ping and shutdown shouldn't be affected by image_path checks even if present (though typically not present)
    ping_req = {
        "request_id": "REQ-000001",
        "cmd": "ping"
    }
    parsed = parse_request(json.dumps(ping_req))
    assert parsed["cmd"] == "ping"

    shutdown_req = {
        "request_id": "REQ-000002",
        "cmd": "shutdown"
    }
    parsed = parse_request(json.dumps(shutdown_req))
    assert parsed["cmd"] == "shutdown"
