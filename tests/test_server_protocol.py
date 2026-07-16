# -*- coding: utf-8 -*-
import pytest
from ve_server.protocol import (
    parse_request, ProtocolError, E_BAD_FIELD
)

def test_parse_request_valid_manual_roi():
    # Valid Manual ROI request
    req = {
        "request_id": "REQ-123456",
        "cmd": "inspect",
        "image_path": "test.png",
        "piece_id": "P001",
        "recipe_name": "TYPE_A",
        "roi_mode": "Manual",
        "roi_rect": {"left": 100, "top": 200, "right": 300, "bottom": 400},
        "param_source": "None"
    }
    import json
    line = json.dumps(req)
    parsed = parse_request(line)
    # Since we convert at the protocol boundary, the parsed dict should have 'x', 'y', 'w', 'h'
    assert parsed["roi_rect"]["x"] == 100
    assert parsed["roi_rect"]["y"] == 200
    assert parsed["roi_rect"]["w"] == 200
    assert parsed["roi_rect"]["h"] == 200

def test_parse_request_invalid_non_dict_roi():
    req = {
        "request_id": "REQ-123456",
        "cmd": "inspect",
        "image_path": "test.png",
        "piece_id": "P001",
        "recipe_name": "TYPE_A",
        "roi_mode": "Manual",
        "roi_rect": [100, 200, 300, 400], # invalid type
        "param_source": "None"
    }
    import json
    line = json.dumps(req)
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(line)
    assert exc_info.value.code == E_BAD_FIELD

def test_parse_request_invalid_missing_key_roi():
    req = {
        "request_id": "REQ-123456",
        "cmd": "inspect",
        "image_path": "test.png",
        "piece_id": "P001",
        "recipe_name": "TYPE_A",
        "roi_mode": "Manual",
        "roi_rect": {"left": 100, "top": 200, "right": 300}, # missing bottom
        "param_source": "None"
    }
    import json
    line = json.dumps(req)
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(line)
    assert exc_info.value.code == E_BAD_FIELD

def test_parse_request_invalid_float_roi():
    req = {
        "request_id": "REQ-123456",
        "cmd": "inspect",
        "image_path": "test.png",
        "piece_id": "P001",
        "recipe_name": "TYPE_A",
        "roi_mode": "Manual",
        "roi_rect": {"left": 100.5, "top": 200, "right": 300, "bottom": 400}, # left is float
        "param_source": "None"
    }
    import json
    line = json.dumps(req)
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(line)
    assert exc_info.value.code == E_BAD_FIELD

def test_parse_request_invalid_bool_roi():
    req = {
        "request_id": "REQ-123456",
        "cmd": "inspect",
        "image_path": "test.png",
        "piece_id": "P001",
        "recipe_name": "TYPE_A",
        "roi_mode": "Manual",
        "roi_rect": {"left": 100, "top": 200, "right": True, "bottom": 400}, # right is bool
        "param_source": "None"
    }
    import json
    line = json.dumps(req)
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(line)
    assert exc_info.value.code == E_BAD_FIELD

def test_parse_request_invalid_illegal_coordinates():
    # right <= left
    req = {
        "request_id": "REQ-123456",
        "cmd": "inspect",
        "image_path": "test.png",
        "piece_id": "P001",
        "recipe_name": "TYPE_A",
        "roi_mode": "Manual",
        "roi_rect": {"left": 300, "top": 200, "right": 300, "bottom": 400},
        "param_source": "None"
    }
    import json
    line = json.dumps(req)
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(line)
    assert exc_info.value.code == E_BAD_FIELD

    # bottom <= top
    req["roi_rect"] = {"left": 100, "top": 400, "right": 300, "bottom": 300}
    line = json.dumps(req)
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(line)
    assert exc_info.value.code == E_BAD_FIELD

def test_parse_request_no_roi_rect_compat():
    # Check that we do NOT retain compatibility with old {x, y, w, h} format
    req = {
        "request_id": "REQ-123456",
        "cmd": "inspect",
        "image_path": "test.png",
        "piece_id": "P001",
        "recipe_name": "TYPE_A",
        "roi_mode": "Manual",
        "roi_rect": {"x": 100, "y": 200, "w": 200, "h": 200},
        "param_source": "None"
    }
    import json
    line = json.dumps(req)
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(line)
    assert exc_info.value.code == E_BAD_FIELD
