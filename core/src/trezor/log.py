import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Any


def _no_op(*args: Any, **kwargs: Any) -> None:
    return None


if __debug__:
    from trezorlog import debug, error, info, warning  # noqa: F401

    _levels = [debug, info, warning, error]
    _min_level = 0  # can be used for manually disabling low-priority logging levels
    debug, info, warning, error = [_no_op] * _min_level + _levels[_min_level:]
else:
    # logging is disabled in non-debug builds
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
