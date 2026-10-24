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


class VaultTestCase(TestCaseWithContext):
    """Explicit unlocked request fixture for tests of protected derivation."""

    def setUp(self):
        from trezorcrypto import SecretOwner, _secret_owner_activate

        from trezor import config

        config.init()
        config.wipe()
        assert config.unlock("", None)
        parent = context.get_context().cache.get_secret_owner()
        self.secret_owner = SecretOwner(parent)
        _secret_owner_activate(self.secret_owner)

    def tearDown(self):
        from trezorcrypto import _secret_owner_activate

        self.secret_owner.destroy()
        _secret_owner_activate(None)


def cache_seed(seed):
    from trezorcrypto import retain_secret, secbytes

    if isinstance(seed, bytes):
        seed = secbytes(seed)
    retain_secret(seed)
    context.get_context().cache.vault_seed.take(seed)


def assert_secret(test, actual, expected):
    """Check every bit of a secret vector through its native MAC operation."""
    from trezor.crypto import hmac

    message = b"protected secret test vector"
    test.assertEqual(
        hmac.tag(hmac.SHA256, actual, message),
        hmac(hmac.SHA256, expected, message).digest(),
    )
