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
        if not utils.USE_THP:
            from storage import cache_codec

            cache_codec.start_session()
        parent = context.get_context().cache.get_secret_owner()
        self.secret_owner = SecretOwner(parent)
        _secret_owner_activate(self.secret_owner)

    def tearDown(self):
        from trezorcrypto import _secret_owner_activate

        owner = getattr(self, "secret_owner", None)
        if owner is not None:
            owner.destroy()
        _secret_owner_activate(None)


def cache_seed(seed):
    from storage import common, device

    common.set_bool(common.APP_DEVICE, device.INITIALIZED, True, public=True)
    from trezorcrypto import secbytes

    from storage.cache_common import APP_COMMON_SEED

    if isinstance(seed, bytes):
        seed = secbytes(seed)
    context.get_context().cache.take_secret(APP_COMMON_SEED, seed)


def assert_cardano_key(test, node, private_key, extension):
    """Check both halves of a Cardano node's expanded key against vectors.

    A deterministic Ed25519 signature depends on the extension (R) and the
    scalar (S), but only on the scalar modulo the group order. Hardened
    derivation hashes the exact bytes of both halves, so a hardened child of
    the node must also match that of a plaintext reference node."""
    from trezor.crypto import cardano
    from trezor.crypto.curve import ed25519

    message = b"protected secret test vector"
    test.assertEqual(
        ed25519.sign_ext(node, message),
        ed25519.sign_ext(private_key, extension, message),
    )
    reference = cardano.from_secret(private_key + extension + node.chain_code())
    child = node.clone()
    child.derive(0x8000_0000)
    reference.derive(0x8000_0000)
    test.assertEqual(child.public_key(), reference.public_key())
