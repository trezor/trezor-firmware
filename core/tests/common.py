import unittest  # noqa: F401
from typing import TYPE_CHECKING, Any

from trezor import utils  # noqa: F401
from trezor.wire import context

from apps.common.paths import HARDENED

if TYPE_CHECKING:
    from collections.abc import Awaitable


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


class TestCaseWithSeed(TestCaseWithContext):
    """
    Patch `apps.common.seed.get_seed` to return the "all" seed.
    """

    def setUpClass(self):
        from mock import MockAsync, patch
        from trezor.crypto import bip39

        from apps.common import seed as seed_module

        super().setUpClass()
        seed = bip39.seed(" ".join(["all"] * 12), "")
        self._seed_patch = patch(seed_module, "get_seed", MockAsync(return_value=seed))
        self._seed_patch.__enter__()

    def tearDownClass(self):
        self._seed_patch.__exit__(None, None, None)
        super().tearDownClass()
