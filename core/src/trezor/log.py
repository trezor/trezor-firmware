import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezorio import WireInterface

if __debug__:
    from trezorlog import debug, error, info, warning  # noqa: F401
else:
    # logging is disabled in non-debug builds
    debug = warning = info = error = lambda *args, **kwargs: None


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
