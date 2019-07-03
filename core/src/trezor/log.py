import sys
import utime
from micropython import const

if False:
    from typing import Any

NOTSET = const(0)
DEBUG = const(10)
INFO = const(20)
WARNING = const(30)
ERROR = const(40)
CRITICAL = const(50)

_leveldict = {
    DEBUG: ("DEBUG", "32"),
    INFO: ("INFO", "36"),
    WARNING: ("WARNING", "33"),
    ERROR: ("ERROR", "31"),
    CRITICAL: ("CRITICAL", "1;31"),
}

level = DEBUG
color = True


def _log(name: str, mlevel: int, msg: str, *args: Any) -> None:
    if __debug__ and mlevel >= level:
        if color:
            fmt = (
                "%d \x1b[35m%s\x1b[0m \x1b["
                + _leveldict[mlevel][1]
                + "m%s\x1b[0m "
                + msg
            )
        else:
            fmt = "%d %s %s " + msg
        print(fmt % ((utime.ticks_us(), name, _leveldict[mlevel][0]) + args))


def debug(name: str, msg: str, *args: Any) -> None:
    _log(name, DEBUG, msg, *args)


def info(name: str, msg: str, *args: Any) -> None:
    _log(name, INFO, msg, *args)


def warning(name: str, msg: str, *args: Any) -> None:
    _log(name, WARNING, msg, *args)


def error(name: str, msg: str, *args: Any) -> None:
    _log(name, ERROR, msg, *args)


def critical(name: str, msg: str, *args: Any) -> None:
    _log(name, CRITICAL, msg, *args)


def exception(name: str, exc: BaseException) -> None:
    _log(name, ERROR, "exception:")
    sys.print_exception(exc)
