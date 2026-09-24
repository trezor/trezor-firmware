# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.wire.errors import AppError

if utils.USE_APP_LOADING:
    from apps.extapp import session as session_module
    from apps.extapp.session import Session


class FakeImage:
    def __init__(self):
        self.stopped = False

    def task_id(self):
        return 0

    def stop(self):
        self.stopped = True


class FailingIo:
    def ipc_send(self, remote, service, message_id, data):
        raise RuntimeError("inbox full")


@unittest.skipUnless(utils.USE_APP_LOADING, "built without app loading")
class TestSessionSend(unittest.TestCase):
    def setUp(self):
        self.io = session_module.io
        session_module.io = FailingIo()
        self.session = Session(FakeImage(), 0, [], [])

    def tearDown(self):
        session_module.io = self.io

    def test_failed_send_stops_app(self):
        with self.assertRaises(AppError):
            self.session.send(0, 0, b"")
        self.assertTrue(self.session.dead)
        self.assertTrue(self.session.image.stopped)

    def test_failed_send_raises(self):
        with self.assertRaises(RuntimeError):
            self.session.send(0, 0, b"", die_on_error=False)
        self.assertFalse(self.session.dead)


if __name__ == "__main__":
    unittest.main()
