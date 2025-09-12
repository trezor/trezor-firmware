from typing import *
from buffer_types import *


# rust/src/micropython/logging.rs
def debug(name: str, msg: str, *args: Any, *, iface: WireInterface | None = None) -> None:
    ...


# rust/src/micropython/logging.rs
def info(name: str, msg: str, *args: Any, *, iface: WireInterface | None = None) -> None:
    ...


# rust/src/micropython/logging.rs
def warning(name: str, msg: str, *args: Any, *, iface: WireInterface | None = None) -> None:
    ...


# rust/src/micropython/logging.rs
def error(name: str, msg: str, *args: Any, *, iface: WireInterface | None = None) -> None:
    ...
