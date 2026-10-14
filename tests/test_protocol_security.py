# -*- coding: utf-8 -*-
"""協定安全性單元測試。

測試 ve_server/protocol.py 中的安全性驗證：
1. 合法影像副檔名通過驗證
2. 非法副檔名遭拒絕 (E_BAD_FIELD)
3. 路徑穿越 (Path Traversal) 遭拒絕 (E_BAD_FIELD)
"""
import pytest
import ve_server.protocol as P


def _make_req(cmd="inspect", image_path="test.png"):
    req = {
        "request_id": "REQ-000001",
        "cmd": cmd,
        "image_path": image_path,
        "roi_mode": "AutoFrame",
    }
    if cmd == "inspect":
        req["param_source"] = "None"
        req["piece_id"] = "P001"
        req["recipe_name"] = "RECIPE_A"
    elif cmd == "teach":
        req["recipe_name"] = "RECIPE_A"
    import json
    return json.dumps(req)


def test_valid_image_extensions():
    valid_exts = [".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]
    for ext in valid_exts:
        raw = _make_req(cmd="inspect", image_path=f"sample{ext}")
        parsed = P.parse_request(raw)
        assert parsed["image_path"] == f"sample{ext}"

        raw_teach = _make_req(cmd="teach", image_path=f"sample{ext}")
        parsed_teach = P.parse_request(raw_teach)
        assert parsed_teach["image_path"] == f"sample{ext}"


def test_invalid_image_extensions():
    invalid_exts = ["sample.txt", "sample.exe", "sample.py", "sample.sh", "sample_no_ext"]
    for img_path in invalid_exts:
        raw = _make_req(cmd="inspect", image_path=img_path)
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(raw)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "extension" in exc_info.value.msg


def test_path_traversal_rejection():
    traversal_paths = [
        "../secret.png",
        "../../etc/passwd.png",
        "C:\\..\\windows\\system32\\cmd.png",
        "images/../other.png",
    ]
    for img_path in traversal_paths:
        raw = _make_req(cmd="inspect", image_path=img_path)
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(raw)
        assert exc_info.value.code == P.E_BAD_FIELD
        assert ".." in exc_info.value.msg
