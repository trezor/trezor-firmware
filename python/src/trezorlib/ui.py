import warnings
from typing import Any


def __getattr__(name: str) -> Any:
    from .cli import ui

    warnings.warn(
        "trezorlib.ui is deprecated and will be removed in 0.21. Use trezorlib.cli.ui instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return getattr(ui, name)
