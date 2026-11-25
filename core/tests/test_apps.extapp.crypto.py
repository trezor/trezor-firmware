# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.wire.errors import DataError

if utils.USE_APP_LOADING:
    from trezor.crypto import bip39
    from trezor.crypto.curve import curve25519, ed25519, nist256p1, secp256k1
    from trezor.wire import context

    from apps.common.keychain import ForbiddenKeyPath, Keychain
    from apps.common.paths import SLIP25_PURPOSE, AlwaysMatchingSchema
    from apps.extapp import crypto
    from apps.extapp.session import MSG_ID_ERROR, SERVICE_CRYPTO


class FakeApi:
    def deserialize_crypto_message(self, data):
        return None


class FakeSession:
    def __init__(self):
        self.sent = []

    def send(self, service, message_id, data):
        self.sent.append((service, message_id, data))

    def die(self, reason):
        raise AssertionError(reason)


class KeychainSession(FakeSession):
    def __init__(self, seed):
        super().__init__()
        self.seed = seed
        self.schemas = [AlwaysMatchingSchema]

    async def keychain(self, curve):
        return Keychain(self.seed, curve, self.schemas)


class FakeMessage:
    message_id = 0  # get_xpub
    data = b""


@unittest.skipUnless(utils.USE_APP_LOADING, "built without app loading")
class TestCryptoHandle(unittest.TestCase):
    def setUp(self):
        self.api = crypto.trezorcrypto_api
        self.handler = crypto._HANDLERS[FakeMessage.message_id]
        crypto.trezorcrypto_api = FakeApi()

    def tearDown(self):
        crypto.trezorcrypto_api = self.api
        crypto._HANDLERS[FakeMessage.message_id] = self.handler

    def handle_raising(self, exc, session):
        async def handler(_session, _obj):
            raise exc

        crypto._HANDLERS[FakeMessage.message_id] = handler
        return await_result(crypto.handle(session, FakeMessage()))

    def test_failure_reported_to_app(self):
        session = FakeSession()
        self.handle_raising(DataError("failed"), session)
        self.assertEqual(session.sent, [(SERVICE_CRYPTO, MSG_ID_ERROR, b"")])

    def test_unexpected_message_propagates(self):
        # e.g. the host sends another request instead of PassphraseAck
        session = FakeSession()
        with self.assertRaises(context.UnexpectedMessageException):
            self.handle_raising(context.UnexpectedMessageException(None), session)
        self.assertEqual(session.sent, [])

    def test_slip25_paths_forbidden(self):
        # even when the manifest matches them, e.g. for signing
        session = KeychainSession(bip39.seed(" ".join(["all"] * 12), ""))
        address_n = [SLIP25_PURPOSE, H_(0), H_(0)]
        with self.assertRaises(ForbiddenKeyPath):
            await_result(
                crypto._ecdsa_sign_digest(
                    session, (0, address_n, b"\x01" * 32, True, 0)
                )
            )
        with self.assertRaises(ForbiddenKeyPath):
            await_result(crypto._get_xpub(session, (0, address_n)))

    def test_get_public_key_formats(self):
        # the formats the apps rely on: raw 32-byte EdDSA keys, and both
        # compressed and uncompressed ECDSA keys
        seed = bip39.seed(" ".join(["all"] * 12), "")
        session = KeychainSession(seed)
        address_n = [H_(44), H_(1), H_(0)]
        curves = (
            ("secp256k1", secp256k1),
            ("nist256p1", nist256p1),
            ("ed25519", ed25519),
            ("curve25519", curve25519),
        )
        for index, (name, curve) in enumerate(curves):
            node = Keychain(seed, name, [AlwaysMatchingSchema]).derive(address_n)
            for compressed in (True, False):
                if name in ("secp256k1", "nist256p1"):
                    expected = curve.publickey(node.private_key(), compressed)
                else:
                    expected = curve.publickey(node.private_key())
                result = await_result(
                    crypto._get_public_key(session, (index, address_n, compressed))
                )
                self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
