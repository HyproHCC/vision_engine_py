# -*- coding: utf-8 -*-
"""協定層：訊息解析/驗證/回應組裝。與 PROTOCOL.md 一一對應。

規則重點：
- 每行 JSON、行尾 \\r\\n（由 server.py 負責加上）
- 回應 ensure_ascii=True
- request_id 原樣回填
- client 字串欄位只允許 ASCII
"""
import json
import os
import time

# ---- engine error codes（PROTOCOL.md 第 9 節）----
E_OK = 0
E_IMAGE_NOT_FOUND = 100
E_IMAGE_LOAD_FAIL = 101
E_FRAME_NOT_FOUND = 102
E_LINES_NOT_FOUND = 103
E_TAUGHT_PARAMS_BAD = 104
E_INTERNAL = 110
E_BAD_JSON = 120
E_UNKNOWN_CMD = 121
E_BAD_FIELD = 122

# ---- status ----
S_OK = "OK"
S_NG = "NG"
S_PLACEMENT = "PLACEMENT_ERROR"
S_DETECTION_ANOMALY = "DETECTION_ANOMALY"
S_ENGINE_ERROR = "ENGINE_ERROR"

VALID_CMDS = ("ping", "inspect", "teach", "shutdown")

# client 送來必須是 ASCII 的字串欄位
ASCII_FIELDS = ("image_path", "piece_id", "recipe_name")


class ProtocolError(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code = code
        self.msg = msg


def parse_request(line: str) -> dict:
    """解析一行請求。失敗丟 ProtocolError。"""
    try:
        req = json.loads(line)
    except Exception as e:
        raise ProtocolError(E_BAD_JSON, "invalid JSON: %s" % e)
    if not isinstance(req, dict):
        raise ProtocolError(E_BAD_JSON, "request must be a JSON object")

    if "request_id" not in req or not isinstance(req["request_id"], str):
        raise ProtocolError(E_BAD_FIELD, "missing/invalid request_id")
    cmd = req.get("cmd")
    if not isinstance(cmd, str):
        raise ProtocolError(E_BAD_FIELD, "missing/invalid cmd")
    if cmd not in VALID_CMDS:
        raise ProtocolError(E_UNKNOWN_CMD, "unknown cmd: %s" % cmd)

    # ASCII 檢查（雙保險；LabVIEW 端已擋一次）
    for f in ASCII_FIELDS:
        v = req.get(f)
        if isinstance(v, str) and not v.isascii():
            raise ProtocolError(E_BAD_FIELD, "field '%s' contains non-ASCII" % f)

    if cmd in ("inspect", "teach"):
        if not isinstance(req.get("image_path"), str) or not req["image_path"]:
            raise ProtocolError(E_BAD_FIELD, "missing image_path")
        # 安全增強：防止目錄穿越並限制 image_path 的副檔名
        path = req["image_path"]
        if ".." in path:
            raise ProtocolError(E_BAD_FIELD, "path traversal detected in image_path")
        _, ext = os.path.splitext(path.lower())
        if ext not in (".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"):
            raise ProtocolError(E_BAD_FIELD, "invalid image_path extension")
        rm = req.get("roi_mode", "AutoFrame")
        if rm not in ("Manual", "AutoFrame"):
            raise ProtocolError(E_BAD_FIELD, "roi_mode must be Manual|AutoFrame")
        if rm == "Manual":
            rr = req.get("roi_rect")
            if (not isinstance(rr, dict) or
                    not all(isinstance(rr.get(k), (int, float))
                           for k in ("left", "top", "right", "bottom"))):
                raise ProtocolError(
                    E_BAD_FIELD,
                    "roi_mode=Manual requires roi_rect{left,top,right,bottom}")
            if rr["right"] <= rr["left"] or rr["bottom"] <= rr["top"]:
                raise ProtocolError(
                    E_BAD_FIELD,
                    "roi_rect requires right>left and bottom>top")
    if cmd == "inspect":
        ps = req.get("param_source", "None")
        if ps not in ("None", "Taught", "Manual"):
            raise ProtocolError(E_BAD_FIELD, "param_source must be None|Taught|Manual")
    return req


def build_response(req: dict, status: str, error_code: int = E_OK,
                   error_msg: str = "", t_start: float = None, **extra) -> dict:
    resp = {
        "request_id": req.get("request_id", ""),
        "cmd": req.get("cmd", ""),
        "status": status,
        "error_code": error_code,
        "error_msg": error_msg,
        "elapsed_ms": round((time.perf_counter() - t_start) * 1000.0, 1) if t_start else 0.0,
    }
    resp.update(extra)
    return resp


def build_error_response(req_or_none, code: int, msg: str, t_start: float = None) -> dict:
    req = req_or_none if isinstance(req_or_none, dict) else {}
    return build_response(req, S_ENGINE_ERROR, code, msg, t_start, defects=[])


def encode_response(resp: dict) -> bytes:
    """組一行回應；ensure_ascii + \\r\\n（LabVIEW CRLF 模式的硬需求）。"""
    return (json.dumps(resp, ensure_ascii=True, separators=(",", ":")) + "\r\n").encode("ascii")
