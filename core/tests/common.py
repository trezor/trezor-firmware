import sys

sys.path.append("../src")

import unittest  # noqa: F401
from typing import TYPE_CHECKING, Any
from ubinascii import hexlify, unhexlify  # noqa: F401

from trezor import utils  # noqa: F401

from apps.common.paths import HARDENED

if TYPE_CHECKING:
    from typing import Awaitable

    from mock import patch as Patch


def H_(x: int) -> int:
    """
    Shortcut function that "hardens" a number in a BIP44 path.
    """
    return x | HARDENED


def await_result(task: Awaitable) -> Any:
    value = None
    while True:
        try:
            result = task.send(value)
        except StopIteration as e:
            return e.value

        if result:
            value = await_result(result)
        else:
            value = None


def await_result_patched(task: Awaitable, patch: Patch | None = None) -> Any:
    if patch is None:
        patch = patch_get_seed()
    with patch:
        return await_result(task=task)


def patch_get_seed(seed: bytes | None = None) -> Patch:
    from trezorcrypto import bip39

    from mock import MockAsync, patch

    from apps.common import seed as seed_module

    return patch(
        seed_module,
        "get_seed",
        MockAsync(return_value=seed or bip39.seed(" ".join(["all"] * 12), "")),
    )
