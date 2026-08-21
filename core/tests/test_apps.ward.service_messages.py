# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import protobuf, utils
from trezor.enums import MessageType
from trezor.messages import (
    WardChainLink,
    WardFlushQueueApplied,
    WardMutationApplied,
    WardPublish,
    WardPublishAck,
    WardPublishConflict,
    WardServiceFetch,
    WardServiceOpen,
    WardServiceOpenAck,
    WardSyncRequest,
    WardSyncRequired,
    WardSyncResponse,
)


def _roundtrip(cls, msg):
    """Encode then decode, with the class passed explicitly.

    `type(msg)` is not accepted by `protobuf.decode` here -- message types are C-backed -- which
    is why the existing protobuf tests name the class too.
    """
    buffer = bytearray(protobuf.encoded_length(msg))
    protobuf.encode(buffer, msg)
    return protobuf.decode(buffer, cls, False)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "WARD is not built in BTC-only firmware")
class TestWardServiceMessages(unittest.TestCase):
    """The service message set exists on the device and survives a round trip.

    Worth asserting for a set this size because the failure mode is silent: a message that is
    declared but never encoded looks perfectly healthy until the first exchange that needs it, and
    the wire id and the class are generated from two different places that have to agree.
    """

    def test_every_service_message_is_reachable_by_wire_id(self):
        """The device resolves a wire id to a class, so a mismatch between the enum and the
        generated class is what would break decoding -- and nothing else would notice."""
        for name in (
            "WardServiceOpen",
            "WardServiceOpenAck",
            "WardSyncRequest",
            "WardSyncResponse",
            "WardServiceFetch",
            "WardSyncRequired",
            "WardPublish",
            "WardPublishAck",
            "WardPublishConflict",
            "WardMutationApplied",
            "WardFlushQueueApplied",
        ):
            wire_id = getattr(MessageType, name)
            resolved = protobuf.type_for_wire("MessageType", wire_id)
            self.assertEqual(resolved.MESSAGE_NAME, name)

    def test_the_open_handshake_round_trips(self):
        got = _roundtrip(WardServiceOpen, WardServiceOpen(protocol_version=1))
        self.assertEqual(got.protocol_version, 1)
        _roundtrip(WardServiceOpenAck, WardServiceOpenAck())

    def test_a_sync_exchange_round_trips(self):
        req = _roundtrip(
            WardSyncRequest,
            WardSyncRequest(
                nonce=b"\x11" * 32,
                ward_id=b"\x22" * 32,
                current_counter=41,
                current_root=b"\x33" * 32,
                current_mac=b"\x44" * 32,
                head_init_sig=b"\x55" * 64,
            )
        )
        self.assertEqual(req.current_counter, 41)
        self.assertEqual(req.head_init_sig, b"\x55" * 64)

        # the chain is what a service build adopts by, so links must survive the trip
        resp = _roundtrip(
            WardSyncResponse,
            WardSyncResponse(
                counter=43,
                mac=b"\x66" * 32,
                timestamp=1700000000,
                wm_signature=b"\x77" * 64,
                links=[
                    WardChainLink(
                        from_counter=41,
                        from_root=b"\x01" * 32,
                        to_counter=42,
                        to_root=b"\x02" * 32,
                        auth_commit=b"\x03" * 32,
                    ),
                    WardChainLink(
                        from_counter=42,
                        from_root=b"\x02" * 32,
                        to_counter=43,
                        to_root=b"\x04" * 32,
                        auth_commit=b"\x05" * 32,
                    ),
                ],
            )
        )
        self.assertEqual(resp.counter, 43)
        self.assertEqual(len(resp.links), 2)
        self.assertEqual(resp.links[1].auth_commit, b"\x05" * 32)

    def test_an_empty_chain_is_distinguishable(self):
        """No links is the ordinary "nothing changed" answer, not a malformed one."""
        resp = _roundtrip(
            WardSyncResponse, WardSyncResponse(counter=41, mac=b"\x66" * 32, wm_signature=b"\x77" * 64)
        )
        self.assertEqual(resp.links, [])

    def test_a_fetch_names_the_head_it_asks_about(self):
        got = _roundtrip(
            WardServiceFetch,
            WardServiceFetch(
                entry_key=b"\xaa" * 32, current_counter=41, current_root=b"\xbb" * 32
            )
        )
        self.assertEqual(got.entry_key, b"\xaa" * 32)
        self.assertEqual(got.current_root, b"\xbb" * 32)

        # an absent root means the empty tree, which must stay distinguishable from a zero root
        empty = _roundtrip(
            WardServiceFetch, WardServiceFetch(entry_key=b"\xaa" * 32, current_counter=0)
        )
        self.assertIsNone(empty.current_root)

    def test_the_sync_required_answer_round_trips(self):
        _roundtrip(WardSyncRequired, WardSyncRequired())

    def test_a_publish_carries_both_authenticators(self):
        """`auth_commit` is for another device of this wallet; `wm_sig` is for the WM, which never
        receives a root. Both travel, and they are not interchangeable."""
        got = _roundtrip(
            WardPublish,
            WardPublish(
                entry_key=b"\xa1" * 32,
                counter=42,
                mac=b"\xa2" * 32,
                auth_commit=b"\xa3" * 32,
                wm_sig=b"\xa4" * 64,
                nonce=b"\xa5" * 32,
            )
        )
        self.assertEqual(got.auth_commit, b"\xa3" * 32)
        self.assertEqual(got.wm_sig, b"\xa4" * 64)
        self.assertEqual(got.nonce, b"\xa5" * 32)

    def test_a_publish_outcome_round_trips_either_way(self):
        ack = _roundtrip(
            WardPublishAck,
            WardPublishAck(
                counter=42, mac=b"\xb1" * 32, timestamp=1, wm_signature=b"\xb2" * 64
            )
        )
        self.assertEqual(ack.counter, 42)

        conflict = _roundtrip(WardPublishConflict, WardPublishConflict(head_counter=43))
        self.assertEqual(conflict.head_counter, 43)

    def test_the_wallet_host_results_carry_no_leaf(self):
        """The point of these being separate messages: an emptied `WardLeafAck` would be read by
        the host as a DELETION, so a service build must answer with a different type entirely."""
        applied = _roundtrip(
            WardMutationApplied, WardMutationApplied(entry_key=b"\xc1" * 32, counter=42)
        )
        self.assertEqual(applied.counter, 42)
        # STRUCTURALLY leafless, not merely left unset: the fields do not exist, so no caller can
        # read an absent content body as a deletion however carelessly it is written.
        self.assertFalse(hasattr(applied, "identity"))
        self.assertFalse(hasattr(applied, "content"))

        flushed = _roundtrip(
            WardFlushQueueApplied,
            WardFlushQueueApplied(entry_key=b"\xc2" * 32, counter=42, remaining=3)
        )
        # `remaining` drives the host's drain loop; dropping it would strand the rest of the queue
        self.assertEqual(flushed.remaining, 3)


if __name__ == "__main__":
    unittest.main()
