import sys
from typing import TYPE_CHECKING

from trezor import log

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Any, ParamSpec, Protocol

    P = ParamSpec("P")

    class LogFunction(Protocol):
        def __call__(self, name: str, msg: str, *args: Any) -> None: ...

    class LogIfaceFunction(Protocol):
        def __call__(
            self, name: str, iface: WireInterface | None, msg: str, *args: Any
        ) -> None: ...


def _wrap_log(log_func: LogFunction) -> LogIfaceFunction:
    def wrapper(
        name: str,
        iface: WireInterface | None,
        msg: str,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if iface is None:
            return log_func(name, msg, *args, **kwargs)

        iface_str = f"\x1b[93m[{iface.__class__.__name__}]\x1b[0m"

        return log_func(name, f"{iface_str} {msg}", *args, **kwargs)

    return wrapper


debug = _wrap_log(log.debug)
info = _wrap_log(log.info)
warning = _wrap_log(log.warning)
error = _wrap_log(log.error)


def exception(name: str, iface: WireInterface | None, exc: BaseException) -> None:
    # we are using `__class__.__name__` to avoid importing ui module
    # we also need to instruct typechecker to ignore the missing argument
    # in ui.Result exception
    if exc.__class__.__name__ == "Result":
        debug(
            name,
            iface,
            "ui.Result: %s",
            exc.value,  # type: ignore [Cannot access attribute "value" for class "BaseException"]
        )
    elif exc.__class__.__name__ == "Cancelled":
        debug(name, iface, "ui.Cancelled")
    else:
        error(name, iface, "exception:")
        # since mypy 0.770 we cannot override sys, so print_exception is unknown
        sys.print_exception(exc)  # type: ignore ["print_exception" is not a known attribute of module]
