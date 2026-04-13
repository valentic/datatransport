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
#   2023-08-17  Todd Valentic
#               Clear handlers when creating
#
#   2026-03-07  Todd Valentic
#               Set handlers on root logger unless standalone. This 
#                   will let loggers in libraries to still log to 
#                   the right formatter/handler through propogation.
#
#   2026-03-09  Todd Valentic
#               Add JSON formatting
#               Use setLevel's ability to handle string input 
#
##########################################################################

import logging

from logging.handlers import RotatingFileHandler
from logging.handlers import SocketHandler
from pythonjsonlogger import jsonlogger


from .utilities import make_path


def setup_log_socket_handler(config, formatter):
    """Add a socket log handler"""

    host = config.get("log.socket.host", "localhost")
    port = config.get_int("log.socket.port", 9020)

    socket_handler = SocketHandler(host, port)
    socket_handler.setFormatter(formatter)

    return socket_handler


def setup_log_file_handler(config, formatter):
    """Add a rotating file log handler"""

    filename = config.get("log.file")
    maxbytes = config.get_bytes("log.maxbytes", "100kb")
    num_backup = config.get_int("log.backupcount", 3)

    make_path(filename)

    rotating_handler = RotatingFileHandler(filename, "a", maxbytes, num_backup)
    rotating_handler.setFormatter(formatter)

    return rotating_handler


def setup_text_formatter(config):
    """Create a text formatter"""

    msgfmt = "[%(asctime)s.%(msecs)03d %(levelname)7s] %(name)s: " 

    if config.get_boolean("log.showthread", False):
        msgfmt += "[%(threadName)s]"

    msgfmt += "%(message)s"

    datefmt = "%Y-%m-%d %H:%M:%S"

    return logging.Formatter(msgfmt, datefmt)

def setup_json_formatter(config):
    """Create a json formatter"""

    msgfmt = "%(asctime)s %(levelname)s %(name)s %(message)s"

    if config.get_boolean("log.showtread", False):
        msgfmt += "%(threadName)s"

    return jsonlogger.JsonFormatter(msgfmt)


def create(config, name, standalone=False):
    """Create a logger for data transport processes"""

    if standalone:
        logger = logging.getLogger(name)
        logger.propagate = False
    else:
        logger = logging.getLogger()

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    match config.get("log.format", "text"):
        case "text":
            formatter = setup_text_formatter(config)
        case "json":
            formatter = setup_json_formatter(config)
            
    if config.get_boolean("log.file.enable", True):
        logger.addHandler(setup_log_file_handler(config, formatter))

    if config.get_boolean("log.socket.enable", True):
        logger.addHandler(setup_log_socket_handler(config, formatter))

    logger.setLevel(config.get("log.level", "info").upper())

    return logging.getLogger(name)
