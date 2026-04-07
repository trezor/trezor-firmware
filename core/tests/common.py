import unittest  # noqa: F401
from typing import Any, Awaitable
from ubinascii import hexlify, unhexlify  # noqa: F401

from trezor import utils  # noqa: F401
from trezor.wire import context

from apps.common.paths import HARDENED


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


class TestCaseWithContext(unittest.TestCase):
    def setUpClass(self):
        if utils.USE_THP:
            from thp_common import create_context

            context.CURRENT_CONTEXT = create_context()
        else:
            from trezor.wire.codec.codec_context import CodecContext

            context.CURRENT_CONTEXT = CodecContext(None, bytearray(64))

    def tearDownClass(self):
        context.CURRENT_CONTEXT = None
