import sys

sys.path.append("../src")

from ubinascii import hexlify, unhexlify  # noqa: F401

import unittest  # noqa: F401

from trezor import utils  # noqa: F401
from apps.common.paths import HARDENED


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


def zcash_parse(data):
    """Parse Zcash test vectors format."""
    attributes = data[1][0].split(", ")
    class TestVector:
        def __init__(self, inner):
            self.inner = inner

        def __getattr__(self, name):
            index = attributes.index(name)
            value = self.inner[index]
            if isinstance(value, str):
                value = unhexlify(value)
            return value

    return map(TestVector, data[2:])
