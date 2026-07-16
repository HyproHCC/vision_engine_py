# -*- coding: utf-8 -*-
"""Rotating log 設定。log 檔一律 UTF-8（避免 CP950 寫入例外）。"""
import logging
import logging.handlers
import os


def setup_logging(cfg: dict) -> logging.Logger:
    os.makedirs(cfg["log_dir"], exist_ok=True)
    logger = logging.getLogger("ve")
    logger.setLevel(getattr(logging, cfg["log_level"].upper(), logging.INFO))
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    fh = logging.handlers.RotatingFileHandler(
        os.path.join(cfg["log_dir"], "ve_server.log"),
        maxBytes=cfg["log_max_bytes"],
        backupCount=cfg["log_backup_count"],
        encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger
