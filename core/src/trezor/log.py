import sys
import utime
from micropython import const
from typing import Any

_DEBUG = const(10)
_INFO = const(20)
_WARNING = const(30)
_ERROR = const(40)
_CRITICAL = const(50)

_leveldict = {
    _DEBUG: ("DEBUG", "32"),
    _INFO: ("INFO", "36"),
    _WARNING: ("WARNING", "33"),
    _ERROR: ("ERROR", "31"),
    _CRITICAL: ("CRITICAL", "1;31"),
}

level = _DEBUG
color = True


def _log(name: str, mlevel: int, msg: str, *args: Any) -> None:
    if __debug__ and mlevel >= level:
        from trezor.loop import this_task

        (level_name, level_style) = _leveldict[mlevel]
        if color:
            fmt = "%d%s \x1b[35m%s\x1b[0m \x1b[" + level_style + "m%s\x1b[0m " + msg
            task_id = f" \x1b[2;37m0x{id(this_task):x}\x1b[0m" if this_task else ""
        else:
            fmt = "%d%s %s %s " + msg
            task_id = f" 0x{id(this_task):x}" if this_task else ""

        fmt_args = (utime.ticks_us(), task_id, name, level_name) + args
        print(fmt % fmt_args)


def debug(name: str, msg: str, *args: Any) -> None:
    _log(name, _DEBUG, msg, *args)


def info(name: str, msg: str, *args: Any) -> None:
    _log(name, _INFO, msg, *args)


def warning(name: str, msg: str, *args: Any) -> None:
    _log(name, _WARNING, msg, *args)


def error(name: str, msg: str, *args: Any) -> None:
    _log(name, _ERROR, msg, *args)


def exception(name: str, exc: BaseException) -> None:
    # we are using `__class__.__name__` to avoid importing ui module
    # we also need to instruct typechecker to ignore the missing argument
    # in ui.Result exception
    if exc.__class__.__name__ == "Result":
        debug(
            name,
            "ui.Result: %s",
            exc.value,  # type: ignore [Cannot access attribute "value" for class "BaseException"]
        )
    elif exc.__class__.__name__ == "Cancelled":
        debug(name, "ui.Cancelled")
    else:
        error(name, "exception:")
        # since mypy 0.770 we cannot override sys, so print_exception is unknown
        sys.print_exception(exc)  # type: ignore ["print_exception" is not a known attribute of module]
