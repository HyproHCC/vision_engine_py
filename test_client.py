# -*- coding: utf-8 -*-
"""簡易測試 client：模擬 LabVIEW 端行為（送一行、收一行、CRLF）。

用法：
  python test_client.py ping
  python test_client.py inspect path/to/img.png
  python test_client.py teach path/to/img.png
  python test_client.py shutdown
  python test_client.py demo          # 連續打 ping + 3 次 inspect（配 --mock server）
"""
import json
import socket
import sys

HOST, PORT = "127.0.0.1", 5710
_req_no = 0


def send_recv(sock, obj):
    global _req_no
    _req_no += 1
    obj["request_id"] = "REQ-%06d" % _req_no
    line = json.dumps(obj, ensure_ascii=True) + "\r\n"
    sock.sendall(line.encode("ascii"))
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(65536)
        if not chunk:
            raise ConnectionError("server closed")
        buf += chunk
    resp = json.loads(buf.split(b"\n", 1)[0].rstrip(b"\r"))
    print(json.dumps(resp, indent=2, ensure_ascii=False))
    assert resp["request_id"] == obj["request_id"], "request_id mismatch!"
    return resp


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ping"
    img = sys.argv[2] if len(sys.argv) > 2 else "mock.png"
    s = socket.create_connection((HOST, PORT), timeout=10)
    try:
        if cmd == "demo":
            send_recv(s, {"cmd": "ping"})
            for _ in range(3):
                send_recv(s, {"cmd": "inspect", "image_path": img,
                              "piece_id": "TEST-001", "recipe_name": "TYPE_A",
                              "roi_mode": "AutoFrame",
                              "angle_tol_deg": 5.0, "param_source": "None"})
            send_recv(s, {"cmd": "teach", "image_path": img,
                          "recipe_name": "TYPE_A", "roi_mode": "AutoFrame",
                          "angle_tol_deg": 5.0})
        elif cmd in ("inspect", "teach"):
            req = {"cmd": cmd, "image_path": img, "recipe_name": "TYPE_A",
                   "roi_mode": "AutoFrame", "angle_tol_deg": 5.0}
            if cmd == "inspect":
                req.update(piece_id="TEST-001", param_source="None")
            send_recv(s, req)
        else:
            send_recv(s, {"cmd": cmd})
    finally:
        s.close()


if __name__ == "__main__":
    main()
