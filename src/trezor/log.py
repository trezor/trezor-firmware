import sys
import utime
from micropython import const

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


def _log(name, mlevel, msg, *args):
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


def debug(name, msg, *args):
    _log(name, DEBUG, msg, *args)


def info(name, msg, *args):
    _log(name, INFO, msg, *args)


def warning(name, msg, *args):
    _log(name, WARNING, msg, *args)


def error(name, msg, *args):
    _log(name, ERROR, msg, *args)


def exception(name, exc):
    _log(name, ERROR, "exception:")
    sys.print_exception(exc)


def critical(name, msg, *args):
    _log(name, CRITICAL, msg, *args)
