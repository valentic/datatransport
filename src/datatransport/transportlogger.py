#!/usr/bin/env python
"""Transport Logger"""

##########################################################################
#
#   Create log handlers
#
#   2022-10-07  Todd Valentic
#               Add missing comment block header
#               Use get_* methods
#
##########################################################################

import logging

from logging.handlers import RotatingFileHandler
from logging.handlers import SocketHandler


from .utilities import make_path


def _setup_log_socket_handler(config, formatter):
    """Add a socket log handler"""

    host = config.get("log.socket.host", "localhost")
    port = config.get_int("log.socket.port", 9020)

    socket_handler = SocketHandler(host, port)
    socket_handler.setFormatter(formatter)

    return socket_handler


def _setup_log_file_handler(config, formatter):
    """Add a rotating file log handler"""

    filename = config.get("log.file")
    maxbytes = config.get_bytes("log.maxbytes", "100kb")
    num_backup = config.get_int("log.backupcount", 3)

    make_path(filename)

    rotating_handler = RotatingFileHandler(filename, "a", maxbytes, num_backup)
    rotating_handler.setFormatter(formatter)

    return rotating_handler


def _setup_log_formatter():
    """Initialize a log formatter"""

    msgfmt = "[%(asctime)s.%(msecs)03d %(levelname)7s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    return logging.Formatter(msgfmt, datefmt)


def create_transport_logger(config, name):
    """Create a logger for data transport processes"""

    level = config.get("log.level", "info")
    formatter = _setup_log_formatter()

    logger = logging.getLogger(name)

    if config.get_boolean("log.file.enable", True):
        logger.addHandler(_setup_log_file_handler(config, formatter))

    if config.get_boolean("log.socket.enable", True):
        logger.addHandler(_setup_log_socket_handler(config, formatter))

    if level == "error":
        logger.setLevel(logging.ERROR)
    if level == "warning":
        logger.setLevel(logging.WARNING)
    elif level == "info":
        logger.setLevel(logging.INFO)
    elif level == "debug":
        logger.setLevel(logging.DEBUG)

    return logger
