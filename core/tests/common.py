import sys

sys.path.append("../src")

from ubinascii import hexlify, unhexlify  # noqa: F401

import unittest  # noqa: F401

from trezor import utils  # noqa: F401
from apps.common import HARDENED


def H_(x: int) -> int:
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
