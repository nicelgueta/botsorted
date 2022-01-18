import logging
from logging.handlers import RotatingFileHandler
import os, sys
from .config import config

levels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "exception": logging.exception,
}


def get_logger(
    name: str,
    level: str = config["logLevel"],
    maxBytes: int = 500000,
    backupCount: int = 10,
):
    logging.basicConfig(
        handlers=[
            RotatingFileHandler(
                f"logs/{name}.log", maxBytes=maxBytes, backupCount=backupCount
            ),
            logging.StreamHandler(sys.stdout),
        ],
        level=levels[level],
        format="[%(asctime)s][%(name)s.%(funcName)s:%(lineno)d][%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logger = logging.getLogger(name)

    return logger


if __name__ == "__main__":
    l = get_logger(__name__)
    l.debug("hello1")
    l.info("hello2")
    l.warning("hello3")
    l.error("hello4")
    l.exception("hello5")
