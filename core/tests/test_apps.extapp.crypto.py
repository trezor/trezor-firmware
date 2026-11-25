# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.wire.errors import DataError

if utils.USE_APP_LOADING:
    from trezor.wire import context

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


if __name__ == "__main__":
    unittest.main()
