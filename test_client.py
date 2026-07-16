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
            # 1st inspect: AutoFrame
            send_recv(s, {"cmd": "inspect", "image_path": img,
                          "piece_id": "TEST-001", "recipe_name": "TYPE_A",
                          "roi_mode": "AutoFrame",
                          "angle_tol_deg": 5.0, "param_source": "None"})
            # 2nd inspect: Manual ROI
            send_recv(s, {"cmd": "inspect", "image_path": img,
                          "piece_id": "TEST-001", "recipe_name": "TYPE_A",
                          "roi_mode": "Manual",
                          "roi_rect": {"left": 500, "top": 480, "right": 3300, "bottom": 2230},
                          "angle_tol_deg": 5.0, "param_source": "None"})
            # 3rd inspect: AutoFrame
            send_recv(s, {"cmd": "inspect", "image_path": img,
                          "piece_id": "TEST-001", "recipe_name": "TYPE_A",
                          "roi_mode": "AutoFrame",
                          "angle_tol_deg": 5.0, "param_source": "None"})
            send_recv(s, {"cmd": "teach", "image_path": img,
                          "recipe_name": "TYPE_A", "roi_mode": "AutoFrame",
                          "angle_tol_deg": 5.0})
        elif cmd in ("inspect", "teach"):
            roi_mode = "AutoFrame"
            roi_rect = None
            if len(sys.argv) > 3 and sys.argv[3].lower() == "manual":
                roi_mode = "Manual"
                roi_rect = {"left": 500, "top": 480, "right": 3300, "bottom": 2230}

            req = {"cmd": cmd, "image_path": img, "recipe_name": "TYPE_A",
                   "roi_mode": roi_mode, "angle_tol_deg": 5.0}
            if roi_rect is not None:
                req["roi_rect"] = roi_rect
            if cmd == "inspect":
                req.update(piece_id="TEST-001", param_source="None")
            send_recv(s, req)
        else:
            send_recv(s, {"cmd": cmd})
    finally:
        s.close()


if __name__ == "__main__":
    main()
