# -*- coding: utf-8 -*-
import json
import sys
import logging
import pytest

import ve_server.protocol as P


def test_encode_response_line_ending():
    """
    1. encode_response 產生的行尾固定為 \\r\\n（LabVIEW CRLF 模式的硬性要求）
    """
    resp = {"request_id": "REQ-0001", "cmd": "ping", "status": "OK"}
    encoded = P.encode_response(resp)
    assert isinstance(encoded, bytes)
    # 行尾必須為 \r\n
    assert encoded.endswith(b"\r\n")
    # 整段 bytes 只有最後一個 \r\n，避免多個行尾
    assert encoded.count(b"\r\n") == 1


def test_encode_response_ensure_ascii():
    """
    2. 回應 JSON 為 ensure_ascii=True（不得出現非 ASCII 位元組）
    """
    # 含有非 ASCII（繁體中文）欄位的回應
    resp = {
        "request_id": "REQ-0002",
        "cmd": "inspect",
        "status": "ENGINE_ERROR",
        "error_msg": "影像載入失敗：測試中文訊息"
    }
    encoded = P.encode_response(resp)

    # 必須可以被純 ascii 解碼
    decoded_str = encoded.decode("ascii")

    # 確保原始中文以 \uXXXX 轉義字元呈現，而不是直接的 UTF-8 位元組
    assert "測試" not in decoded_str
    assert "\\u" in decoded_str

    # 嘗試用 json 解析解碼後的字串，確保內容正確還原
    parsed = json.loads(decoded_str)
    assert parsed["error_msg"] == "影像載入失敗：測試中文訊息"


def test_client_fields_non_ascii():
    """
    3. client 字串欄位含非 ASCII 時回 PROTOCOL.md §9 規定的錯誤碼 (122)
    """
    # 基準正確的 JSON 請求
    base_inspect_req = {
        "request_id": "REQ-1001",
        "cmd": "inspect",
        "image_path": "D:/VisionWork/img.png",
        "piece_id": "P2026-001",
        "recipe_name": "TYPE_A"
    }

    # 3.1 image_path 含有非 ASCII 字元
    req_bad_path = base_inspect_req.copy()
    req_bad_path["image_path"] = "D:/VisionWork/測試圖片.png"
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request(json.dumps(req_bad_path))
    assert excinfo.value.code == P.E_BAD_FIELD  # 122
    assert "image_path" in excinfo.value.msg

    # 3.2 piece_id 含有非 ASCII 字元
    req_bad_piece = base_inspect_req.copy()
    req_bad_piece["piece_id"] = "P2026-測試"
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request(json.dumps(req_bad_piece))
    assert excinfo.value.code == P.E_BAD_FIELD  # 122
    assert "piece_id" in excinfo.value.msg

    # 3.3 recipe_name 含有非 ASCII 字元
    req_bad_recipe = base_inspect_req.copy()
    req_bad_recipe["recipe_name"] = "配方A"
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request(json.dumps(req_bad_recipe))
    assert excinfo.value.code == P.E_BAD_FIELD  # 122
    assert "recipe_name" in excinfo.value.msg

    # 3.4 允許其他無限制欄位含有非 ASCII (如客製額外參數)
    req_extra_field = base_inspect_req.copy()
    req_extra_field["extra_comment"] = "備註"
    parsed = P.parse_request(json.dumps(req_extra_field))
    assert parsed["extra_comment"] == "備註"


def test_unknown_cmd_and_validation():
    """
    4. 未知指令的錯誤回應
    """
    # 4.1 未知指令
    req_unknown = {
        "request_id": "REQ-2001",
        "cmd": "fly_to_moon"
    }
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request(json.dumps(req_unknown))
    assert excinfo.value.code == P.E_UNKNOWN_CMD  # 121

    # 4.2 欄位缺漏/型別錯誤測試
    # 缺 request_id
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request(json.dumps({"cmd": "ping"}))
    assert excinfo.value.code == P.E_BAD_FIELD  # 122

    # 缺 cmd
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request(json.dumps({"request_id": "REQ-1"}))
    assert excinfo.value.code == P.E_BAD_FIELD  # 122

    # cmd 型別錯誤
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request(json.dumps({"request_id": "REQ-1", "cmd": 123}))
    assert excinfo.value.code == P.E_BAD_FIELD  # 122

    # invalid JSON
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request("{invalid_json}")
    assert excinfo.value.code == P.E_BAD_JSON  # 120

    # Manual roi_mode 缺少 roi_rect
    req_manual_bad = {
        "request_id": "REQ-1",
        "cmd": "inspect",
        "image_path": "D:/img.png",
        "roi_mode": "Manual"
    }
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request(json.dumps(req_manual_bad))
    assert excinfo.value.code == P.E_BAD_FIELD  # 122

    # Manual roi_mode roi_rect right <= left
    req_manual_bad2 = {
        "request_id": "REQ-1",
        "cmd": "inspect",
        "image_path": "D:/img.png",
        "roi_mode": "Manual",
        "roi_rect": {"left": 100, "top": 50, "right": 90, "bottom": 150}
    }
    with pytest.raises(P.ProtocolError) as excinfo:
        P.parse_request(json.dumps(req_manual_bad2))
    assert excinfo.value.code == P.E_BAD_FIELD  # 122


def test_request_id_fillback():
    """
    5. request_id 原樣回填
    """
    # 5.1 正常回應回填
    req = {"request_id": "REQ-SPECIFIC-999", "cmd": "ping"}
    resp = P.build_response(req, P.S_OK)
    assert resp["request_id"] == "REQ-SPECIFIC-999"

    # 5.2 錯誤回應回填
    err_resp = P.build_error_response(req, P.E_BAD_FIELD, "Invalid field value")
    assert err_resp["request_id"] == "REQ-SPECIFIC-999"

    # 5.3 當 request 為 None 時的回填預設值
    err_resp_none = P.build_error_response(None, P.E_BAD_JSON, "Invalid JSON")
    assert err_resp_none["request_id"] == ""


class _FakeConn:
    """假 socket：一次餵入固定 bytes，收集 server 送出的 bytes。"""

    def __init__(self, rx: bytes):
        self._rx = rx
        self.sent = b""

    def recv(self, n):
        chunk, self._rx = self._rx[:n], self._rx[n:]
        return chunk  # 餵完回 b""，_serve_client 視為 client 斷線

    def sendall(self, data):
        self.sent += data


def _serve_lines(raw: bytes):
    """把 raw bytes 餵進真正的 server 路徑（_serve_client），回傳解析後的回應列表。"""
    from ve_server.dispatcher import Dispatcher
    from ve_server.server import _serve_client

    cfg = {
        "host": "127.0.0.1",
        "port": 5710,
        "ng_dir": "MOCK/ng",
        "algo": {},
        "cleanup_on_inspect": False,
    }
    conn = _FakeConn(raw)
    shutdown = _serve_client(conn, Dispatcher(cfg, logging.getLogger("test_server"), mock=True),
                             logging.getLogger("test_server"))
    assert shutdown is False

    lines = conn.sent.split(b"\r\n")
    assert lines[-1] == b""  # 每行回應都以 \r\n 結尾
    return [json.loads(line) for line in lines[:-1]]


def test_parse_error_request_id_fillback_via_server():
    """
    5b. parse 失敗時的 request_id 回填，走真正的 server 路徑（_serve_client）：
        - 該行仍解得出合法 request_id（未知 cmd、欄位錯誤）→ 原樣回填
        - 整行壞損（bad JSON、缺 request_id）→ 回空字串
    """
    responses = _serve_lines(
        b'{"request_id":"REQ-3001","cmd":"fly_to_moon"}\r\n'
        b'{"request_id":"REQ-3002","cmd":123}\r\n'
        b'{invalid json}\r\n'
        b'{"cmd":"ping"}\r\n'
    )
    assert len(responses) == 4
    unknown_cmd, bad_cmd_type, bad_json, missing_rid = responses

    # 未知 cmd：request_id 必須原樣回填（PROTOCOL.md §1），否則 LabVIEW 端
    # 會把這行錯誤回應當 request_id 不符丟棄，卡到 timeout 才報 5401
    assert unknown_cmd["status"] == P.S_ENGINE_ERROR
    assert unknown_cmd["error_code"] == P.E_UNKNOWN_CMD  # 121
    assert unknown_cmd["request_id"] == "REQ-3001"
    assert unknown_cmd["cmd"] == "fly_to_moon"

    # cmd 型別錯誤：request_id 回填；cmd 非字串不得原樣塞回（回應須全 ASCII 字串欄位）
    assert bad_cmd_type["error_code"] == P.E_BAD_FIELD  # 122
    assert bad_cmd_type["request_id"] == "REQ-3002"
    assert bad_cmd_type["cmd"] == ""

    # bad JSON：解不出 request_id，回空字串
    assert bad_json["error_code"] == P.E_BAD_JSON  # 120
    assert bad_json["request_id"] == ""

    # 缺 request_id：無合法值可回填，回空字串
    assert missing_rid["error_code"] == P.E_BAD_FIELD  # 122
    assert missing_rid["request_id"] == ""


def test_mock_dispatcher_rotation_and_no_cv2():
    """
    6. mock 模式 dispatcher 的 verdict 輪替，且 mock 路徑不 import cv2
    """
    # 確保在匯入 Dispatcher 且執行 Mock 時，沒有匯入 cv2
    sys.modules.pop("cv2", None)
    sys.modules.pop("ve_server.engine", None)
    sys.modules.pop("ve_server.dispatcher", None)

    from ve_server.dispatcher import Dispatcher

    assert "cv2" not in sys.modules

    logger = logging.getLogger("test_mock")
    cfg = {
        "host": "127.0.0.1",
        "port": 5710,
        "ng_dir": "MOCK/ng",
        "algo": {},
        "cleanup_on_inspect": False
    }

    dispatcher = Dispatcher(cfg, logger, mock=True)
    assert "cv2" not in sys.modules

    req = {
        "request_id": "REQ-MOCK",
        "cmd": "inspect",
        "image_path": "mock.png"
    }

    # 驗證四態/三態輪替（實際程式行為為四態：OK -> NG -> PLACEMENT_ERROR -> DETECTION_ANOMALY -> OK ...）
    expected_states = [P.S_OK, P.S_NG, P.S_PLACEMENT, P.S_DETECTION_ANOMALY]

    # 跑兩個循環（共 8 次）
    for i in range(8):
        resp, shutdown = dispatcher.handle(req)
        assert not shutdown
        assert "cv2" not in sys.modules

        expected_status = expected_states[i % 4]
        assert resp["status"] == expected_status
        assert resp["request_id"] == "REQ-MOCK"

        # 針對個別狀態驗證關鍵欄位
        if expected_status == P.S_OK:
            assert resp["defects"] == []
            assert resp["ng_image_path"] == ""
        elif expected_status == P.S_NG:
            assert len(resp["defects"]) == 2
            assert resp["ng_image_path"] == "MOCK/ng/fake.png"
        elif expected_status == P.S_PLACEMENT:
            assert resp["defects"] == []
            assert resp["lines_found"] == 0
        elif expected_status == P.S_DETECTION_ANOMALY:
            assert resp["defects"] == []
            assert "reason_codes" in resp
            assert "COUNT_MISMATCH_V" in resp["reason_codes"]
