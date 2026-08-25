# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import loop, protobuf, utils
from trezor.messages import WardEntryAck, WardServiceFetch, WardSyncRequired
from trezor.wire import DataError
from trezor.wire.protocol_common import Message

from apps.ward import root as R
from apps.ward import service as S


def _encode(msg):
    buffer = bytearray(protobuf.encoded_length(msg))
    protobuf.encode(buffer, msg)
    return bytes(buffer)


def _as_message(msg):
    return Message(msg.MESSAGE_WIRE_TYPE, _encode(msg))


class _FakeChannel:
    """Records what was written and hands back a canned answer.

    Only what `_rpc` actually touches: the point of the exercise is the request it builds and the
    answer it will accept, not THP itself. That does include the identity a real channel is logged
    and torn down by -- `_desynchronised` closes the channel, and the RPC logs which one it used --
    so those are here as well, cheaply.
    """

    def __init__(self, answer=None, answer_session_id=None):
        self.written = []
        self._answer = answer
        self._answer_session_id = answer_session_id
        self.channel_id = 0x1234
        self.iface = None
        self.cleared = None

    async def write(self, msg, session_id=0):
        self.written.append((session_id, msg))

    async def read(self):
        if self._answer is None:
            raise AssertionError("read() called with no answer prepared")
        sid = self._answer_session_id
        return (sid, self._answer)

    def clear(self, exc=None):
        self.cleared = exc


@unittest.skipUnless(not utils.BITCOIN_ONLY, "WARD is not built in BTC-only firmware")
class TestWardServiceBinding(unittest.TestCase):
    """The pointer that says which channel is the service."""

    def setUp(self):
        S.clear_binding()

    def test_nothing_is_bound_to_begin_with(self):
        self.assertIsNone(S.get_binding())

    def test_every_field_comes_back(self):
        """The interface number is part of it on purpose: a channel id can be closed and
        reallocated on a DIFFERENT interface, so the id alone cannot answer "is this still my
        service?"."""
        S.set_binding(7, 0x3F9C, 5)
        self.assertEqual(S.get_binding(), (7, 0x3F9C, 5))

    def test_it_can_be_forgotten(self):
        S.set_binding(7, 1, 0)
        S.clear_binding()
        self.assertIsNone(S.get_binding())

    def test_a_full_width_channel_id_survives(self):
        """Two bytes, so the top of the range must not be truncated."""
        S.set_binding(255, 0xFFFF, 255)
        self.assertEqual(S.get_binding(), (255, 0xFFFF, 255))


@unittest.skipUnless(not utils.BITCOIN_ONLY, "WARD is not built in BTC-only firmware")
class TestWardServiceRpc(unittest.TestCase):
    """Asking the service a question and accepting its answer.

    `loop.race` is stubbed for these: what it does -- return whichever finished first -- is
    library behaviour, and stubbing it is what makes the two outcomes ("an answer" and "no
    answer") reachable without waiting for a real deadline.
    """

    def setUp(self):
        self._real_race = loop.race
        self._real_channel = S._service_channel
        self._real_counter = R.get_counter
        self._real_root = R.get_root

    def tearDown(self):
        loop.race = self._real_race
        S._service_channel = self._real_channel
        R.get_counter = self._real_counter
        R.get_root = self._real_root

    def _install(self, channel, session_id=3, answered=True):
        S._service_channel = lambda: (channel, session_id)

        async def _race(read_task, sleep_task):
            if answered:
                return await read_task
            # What a real race returns when the deadline wins: `loop.sleep` yields an int.
            return 0

        loop.race = _race

    def test_it_asks_on_the_service_session_and_returns_the_answer(self):
        channel = _FakeChannel(_as_message(WardEntryAck()), answer_session_id=3)
        self._install(channel)

        answer = await_result(S._rpc(WardServiceFetch(entry_key=b"\x01" * 32), WardEntryAck))

        # By wire type: these classes are C-backed and `isinstance` refuses them.
        self.assertEqual(answer.MESSAGE_WIRE_TYPE, WardEntryAck.MESSAGE_WIRE_TYPE)
        # ...written on the service's own session, not session 0
        self.assertEqual(channel.written[0][0], 3)

    def test_an_answer_on_another_session_is_refused(self):
        """A reply carrying someone else's session id is not this conversation's reply, and
        acting on it would mean acting on a message meant for something else."""
        channel = _FakeChannel(_as_message(WardEntryAck()), answer_session_id=4)
        self._install(channel)

        with self.assertRaises(DataError):
            await_result(S._rpc(WardServiceFetch(entry_key=b"\x01" * 32), WardEntryAck))

    def test_an_unexpected_type_is_refused(self):
        """Not interpreted, not ignored: the daemon is the only party on this channel, so a
        surprise means the conversation has desynchronised."""
        channel = _FakeChannel(_as_message(WardSyncRequired()), answer_session_id=3)
        self._install(channel)

        with self.assertRaises(DataError):
            await_result(S._rpc(WardServiceFetch(entry_key=b"\x01" * 32), WardEntryAck))

    def test_no_answer_fails_closed(self):
        """A daemon that stops answering must not hang the workflow the user is waiting on.
        Hanging is the one failure mode a fail-closed read does not otherwise have."""
        channel = _FakeChannel()
        self._install(channel, answered=False)

        with self.assertRaises(DataError):
            await_result(S._rpc(WardServiceFetch(entry_key=b"\x01" * 32), WardEntryAck))

    def test_an_unbound_service_is_not_asked(self):
        S.clear_binding()
        with self.assertRaises(DataError):
            S._service_channel()

    def test_fetch_names_the_head_the_device_holds(self):
        """HEAD-AWARE, which is the whole difference from the connect-mode request. Both fields:
        several roots may share a counter across forks, so the counter alone does not name a head.
        """
        channel = _FakeChannel(_as_message(WardEntryAck()), answer_session_id=3)
        self._install(channel)

        root = b"\x77" * 32

        async def _counter():
            return 41

        async def _root():
            return root

        R.get_counter = _counter
        R.get_root = _root

        await_result(S.fetch(b"\x02" * 32))

        _sid, request = channel.written[0]
        self.assertEqual(request.MESSAGE_WIRE_TYPE, WardServiceFetch.MESSAGE_WIRE_TYPE)
        self.assertEqual(request.entry_key, b"\x02" * 32)
        self.assertEqual(request.current_counter, 41)
        self.assertEqual(request.current_root, root)

    def test_fetch_refuses_rather_than_serving_an_unverifiable_proof(self):
        """`WardSyncRequired` is an answer, not a failure -- but until a sync can be driven from
        here it has to fail the read. The direction matters: a read that fell back to anything
        else would be a way to force an old value onto the screen."""
        channel = _FakeChannel(_as_message(WardSyncRequired()), answer_session_id=3)
        self._install(channel)

        async def _counter():
            return 0

        async def _root():
            return None

        R.get_counter = _counter
        R.get_root = _root

        with self.assertRaises(DataError):
            await_result(S.fetch(b"\x02" * 32))


if __name__ == "__main__":
    unittest.main()
