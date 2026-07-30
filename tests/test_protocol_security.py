# -*- coding: utf-8 -*-
import pytest
import ve_server.protocol as P


def test_valid_image_paths_allowed():
    # 測試合法影像路徑與副檔名
    req = {
        "request_id": "REQ-000001",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/img_20260706_101500_001.png",
        "roi_mode": "AutoFrame",
        "param_source": "None"
    }
    # 應能正常解析無拋出 Exception
    import json
    parsed = P.parse_request(json.dumps(req))
    assert parsed["image_path"] == req["image_path"]

    # 測試其他合法的影像副檔名
    for ext in (".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"):
        req["image_path"] = f"C:\\images\\sample{ext}"
        parsed = P.parse_request(json.dumps(req))
        assert parsed["image_path"] == req["image_path"]


def test_path_traversal_rejected():
    # 測試含有路徑穿越 (..) 之惡意路徑應被拒絕
    bad_paths = [
        "../etc/passwd",
        "D:/VisionWork/../sensitive.png",
        "C:\\images\\..\\win.ini",
        "images/../../etc/shadow.png"
    ]
    for p in bad_paths:
        req = {
            "request_id": "REQ-000002",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        import json
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(json.dumps(req))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "path traversal" in exc_info.value.msg


def test_invalid_extensions_rejected():
    # 測試非影像副檔名或惡意副檔名應被拒絕
    bad_paths = [
        "D:/VisionWork/img.txt",
        "C:\\Windows\\win.ini",
        "D:/VisionWork/exploit.json",
        "D:/VisionWork/payload.sh",
        "D:/VisionWork/malicious.png.exe",
        "D:/VisionWork/no_extension"
    ]
    for p in bad_paths:
        req = {
            "request_id": "REQ-000003",
            "cmd": "inspect",
            "image_path": p,
            "roi_mode": "AutoFrame",
            "param_source": "None"
        }
        import json
        with pytest.raises(P.ProtocolError) as exc_info:
            P.parse_request(json.dumps(req))
        assert exc_info.value.code == P.E_BAD_FIELD
        assert "invalid image file extension" in exc_info.value.msg
