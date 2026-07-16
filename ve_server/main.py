# -*- coding: utf-8 -*-
"""VisionEngine server 進入點。

用法：
  python -m ve_server.main            # 正常模式（需 opencv、numpy）
  python -m ve_server.main --mock     # mock 模式（免 opencv，離線開發 LabVIEW 用）
  python -m ve_server.main --port 5711 --config D:/path/config.json
"""
import argparse
import sys

from .config import load_config, SERVER_VERSION
from .logsetup import setup_logging
from .server import serve_forever


def main(argv=None):
    ap = argparse.ArgumentParser(description="VisionEngine TCP server")
    ap.add_argument("--mock", action="store_true",
                    help="mock/offline mode (no OpenCV required)")
    ap.add_argument("--host", default=None)
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--config", default=None, help="path to config.json")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    if args.host:
        cfg["host"] = args.host
    if args.port:
        cfg["port"] = args.port

    logger = setup_logging(cfg)
    logger.info("VisionEngine server v%s starting (config=%s)",
                SERVER_VERSION, cfg["_config_path"])
    try:
        serve_forever(cfg, logger, mock=args.mock)
    except KeyboardInterrupt:
        logger.info("interrupted, exiting")
    except Exception:
        logger.exception("fatal error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
