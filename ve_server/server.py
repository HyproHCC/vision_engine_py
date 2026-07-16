# -*- coding: utf-8 -*-
"""TCP server 主迴圈。

設計對應 LabVIEW 端行為：
- 單一客戶端（ENG_Connection FGV），client 斷線後回到 accept 等重連
- 一問一答、循序處理（主程式狀態機保證不會併發送指令）
- 每行回應以 \\r\\n 結尾（protocol.encode_response 已處理）
- 收到 shutdown：回應送出後結束行程
"""
import socket

from . import protocol as P
from .dispatcher import Dispatcher

RECV_CHUNK = 65536
MAX_LINE = 4 * 1024 * 1024  # taught_params 帶 positions 陣列，放寬上限


def serve_forever(cfg: dict, logger, mock: bool = False):
    dispatcher = Dispatcher(cfg, logger, mock=mock)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((cfg["host"], cfg["port"]))
    srv.listen(1)
    logger.info("VisionEngine server listening on %s:%d (mock=%s)",
                cfg["host"], cfg["port"], mock)

    shutdown = False
    while not shutdown:
        conn, addr = srv.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        logger.info("client connected: %s", addr)
        shutdown = _serve_client(conn, dispatcher, logger)
        try:
            conn.close()
        except OSError:
            pass
        logger.info("client disconnected")

    srv.close()
    logger.info("server shutdown complete")


def _serve_client(conn: socket.socket, dispatcher: Dispatcher, logger) -> bool:
    """回傳 True 表示收到 shutdown 指令。"""
    buf = b""
    while True:
        # 先看緩衝區有沒有完整行
        nl = buf.find(b"\n")
        if nl < 0:
            if len(buf) > MAX_LINE:
                logger.error("line too long, dropping connection")
                return False
            try:
                chunk = conn.recv(RECV_CHUNK)
            except OSError:
                return False
            if not chunk:
                return False  # client 斷線
            buf += chunk
            continue

        line = buf[:nl].rstrip(b"\r")
        buf = buf[nl + 1:]
        if not line.strip():
            continue

        # 解析（容忍 client 端可能的 UTF-8；協定要求 ASCII，解析後再驗）
        try:
            text = line.decode("utf-8")
        except UnicodeDecodeError:
            _send(conn, P.build_error_response(
                None, P.E_BAD_JSON, "line is not valid UTF-8/ASCII"), logger)
            continue

        try:
            req = P.parse_request(text)
        except P.ProtocolError as e:
            logger.warning("bad request: [%d] %s", e.code, e.msg)
            _send(conn, P.build_error_response(None, e.code, e.msg), logger)
            continue

        resp, shutdown = dispatcher.handle(req)
        if not _send(conn, resp, logger):
            return False
        if shutdown:
            logger.info("shutdown requested by client")
            return True


def _send(conn: socket.socket, resp: dict, logger) -> bool:
    try:
        conn.sendall(P.encode_response(resp))
        return True
    except OSError as e:
        logger.warning("send failed: %s", e)
        return False
