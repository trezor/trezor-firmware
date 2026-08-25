import sys
from typing import TYPE_CHECKING

from . import utils

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Any


def _no_op(name: str, msg: str, *args: Any, iface: WireInterface | None = None) -> None:
    return None


if utils.USE_DBG_CONSOLE:
    from trezorlog import debug, error, info, init, warning  # noqa: F401

    _levels = [debug, info, warning, error]
    _min_level = 0  # can be used for manually disabling low-priority logging levels
    debug, info, warning, error = [_no_op] * _min_level + _levels[_min_level:]
    init(_min_level)  # initialize rust logging connector

    if utils.USE_WARD_SERVICE_CHANNEL:
        import trezorio

        # EVERY LINE ABOUT THE WARD SERVICE INTERFACE CARRIES THE WORD, so one grep collects the
        # whole conversation. Done here rather than in each message because most of the lines that
        # matter are not WARD's own: the interesting trace runs through `trezor.wire.thp.channel`,
        # `received_message_handler` and `interface_context`, which log for whichever interface they
        # are serving and cannot name this one.
        #
        # THE INTERFACE IS WHAT IS TESTED, not the module emitting the line, because that is the
        # only thing that distinguishes the two conversations. It also cannot be read off the log
        # otherwise: the iface prefix Rust prints is the interface TYPE's name, so the wallet
        # interface and this one both appear as `[USBIF]`.
        _WARD_IFACE_NUM = trezorio.USBIF_WARD

        def _ward_tagged(log_fn: Any) -> Any:
            def wrapper(
                name: str,
                msg: str,
                *args: Any,
                iface: WireInterface | None = None,
            ) -> None:
                if iface is not None and iface.iface_num() == _WARD_IFACE_NUM:
                    msg = "WARD " + msg
                log_fn(name, msg, *args, iface=iface)

            return wrapper

        # `_no_op` is wrapped too when a level is disabled, which costs a call and a comparison on
        # a path that does nothing. Left alone deliberately: this whole block exists only in a
        # debug build, and special-casing it would mean two ways for the levels to be assembled.
        debug, info, warning, error = [
            _ward_tagged(fn) for fn in (debug, info, warning, error)
        ]
else:
    debug = warning = info = error = _no_op


def exception(
    name: str, exc: BaseException, *, iface: WireInterface | None = None
) -> None:
    # we are using `__class__.__name__` to avoid importing ui module
    # we also need to instruct typechecker to ignore the missing argument
    # in ui.Result exception
    if exc.__class__.__name__ == "Result":
        debug(
            name,
            "ui.Result: %s",
            exc.value,  # type: ignore [Cannot access attribute "value" for class "BaseException"]
            iface=iface,
        )
    elif exc.__class__.__name__ == "Cancelled":
        debug(name, "ui.Cancelled", iface=iface)
    else:
        error(name, "exception:", iface=iface)
        # since mypy 0.770 we cannot override sys, so print_exception is unknown
        sys.print_exception(exc)  # type: ignore ["print_exception" is not a known attribute of module]
