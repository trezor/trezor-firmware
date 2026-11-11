# flake8: noqa: F403,F405
from common import *  # isort:skip

import gc
from struct import pack

from trezor import loop, protobuf
from trezor.enums import MessageType as MT

if utils.USE_WARD:
    from trezor.messages import WARDProofAck, WARDServiceOpen
    from trezor.wire import DataError
    from trezor.wire.codec.streaming import StreamCodec

    from apps.common.ward import make_leaf_content, make_leaf_identity
    from apps.ward import leaf, trie


def encoded(message):
    buf = bytearray(protobuf.encoded_length(message))
    protobuf.encode(buf, message)
    return bytes(buf)


def reports(kind, data):
    first = b"?##" + pack(">HL", kind, len(data)) + data[:55]
    result = [first + bytes(64 - len(first))]
    for start in range(55, len(data), 63):
        frame = b"?" + data[start : start + 63]
        result.append(frame + bytes(64 - len(frame)))
    return result


class FakeInterface:
    RX_PACKET_LEN = 64
    TX_PACKET_LEN = 64

    def __init__(self, incoming):
        self.incoming = incoming
        self.written = []

    def iface_num(self):
        return 0

    def read(self, buffer, offset):
        if not self.incoming:
            return 0
        buffer[:] = self.incoming.pop(0)
        return 64

    def write(self, buffer):
        self.written.append(bytes(buffer))
        return 64


@unittest.skipUnless(utils.USE_WARD, "WARD is not enabled")
class TestWardStreaming(unittest.TestCase):
    def setUp(self):
        self.wait = loop.wait
        self.race = loop.race

        async def ready():
            return 64

        async def first(task, ignored):
            return await task

        loop.wait = lambda _event: ready()
        loop.race = first

    def tearDown(self):
        loop.wait = self.wait
        loop.race = self.race

    def decode(self, data, kind=None):
        if kind is None:
            kind = MT.WARDProofAck
        iface = FakeInterface(reports(kind, data))
        codec = StreamCodec(iface)
        result = await_result(codec.read((kind,)))
        self.assertEqual(len(codec.report), 64)
        self.assertEqual(iface.incoming, [])
        return result

    def test_maximum_depth_membership_proof_exceeds_old_shared_buffer(self):
        key = bytes(32)
        id_part = leaf.encode_identity(b"i" * 32, key, "address", b"addr", b"bitcoin")
        val_part = leaf.encode_content(b"v" * 32, key, "address", 1, b"label")
        path = [bit.to_bytes(2, "big") + b"s" * 32 for bit in range(255, -1, -1)]
        root = trie.reconstruct(
            leaf.leaf_hash(key, "address", id_part, val_part), path, key
        )
        message = WARDProofAck(
            proof=path,
            identity=make_leaf_identity("address", id_part),
            content=make_leaf_content(val_part),
        )
        payload = encoded(message)
        self.assertTrue(len(payload) > 8704)
        decoded = self.decode(payload)
        self.assertEqual(decoded.proof, path)
        self.assertTrue(
            trie.verify_proof(key, "address", id_part, val_part, decoded.proof, root)
        )
        print(
            "WARD maximum-depth membership: wire payload=%d, private report=64"
            % len(payload)
        )

    def test_all_hashes_can_cross_report_boundaries(self):
        path = [
            bit.to_bytes(2, "big") + bytes([bit]) * 32 for bit in range(255, -1, -1)
        ]
        payload = encoded(
            WARDProofAck(
                proof=path, witness_entry_key=b"k" * 32, witness_commit=b"h" * 32
            )
        )
        self.assertEqual(len(payload), 9284)
        decoded = self.decode(payload)
        self.assertEqual(decoded.proof, path)
        self.assertEqual(decoded.witness_commit, b"h" * 32)

    def test_257_hops_are_refused(self):
        payload = encoded(WARDProofAck(proof=[bytes(34)] * 257))
        with self.assertRaises(DataError):
            self.decode(payload)

    def test_malformed_proof_length_is_refused_before_allocating_body(self):
        with self.assertRaises(DataError):
            self.decode(b"\x12\xff\x3f")

    def test_truncated_nested_field_is_refused(self):
        with self.assertRaises(DataError):
            self.decode(b"\x62\x40\x08\x00")

    def test_duplicate_fields_are_refused(self):
        with self.assertRaises(DataError):
            self.decode(b"\x78\x00\x78\x01")

    def test_large_unknown_field_is_discarded_without_a_message_buffer(self):
        self.assertEqual(self.decode(b"\x9a\x06\x80\x80\x01" + bytes(16384)).proof, [])

    def test_encoder_uses_the_same_single_report_for_large_messages(self):
        msg = WARDProofAck(proof=[bytes(34)] * 256)
        expected = reports(MT.WARDProofAck, encoded(msg))
        iface = FakeInterface([])
        codec = StreamCodec(iface)
        report = codec.report
        await_result(codec.write(msg))
        self.assertEqual(iface.written, expected)
        self.assertIs(codec.report, report)

    def test_native_encoder_windows_match_full_encoding(self):
        msg = WARDServiceOpen(protocol_version=1, close=True)
        full = encoded(msg)
        for width in (1, 2, 3, 64):
            result = bytearray()
            for offset in range(0, len(full), width):
                window = bytearray(width)
                count = protobuf.encode_range(window, msg, offset)
                result.extend(window[:count])
            self.assertEqual(result, full)

    def test_report_buffer_cannot_be_smaller_than_the_usb_report(self):
        class SmallInterface(FakeInterface):
            RX_PACKET_LEN = 32

        with self.assertRaises(ValueError):
            StreamCodec(SmallInterface([]))

    def test_private_codec_allocation_is_small(self):
        iface = FakeInterface([])
        gc.collect()
        before = gc.mem_free()
        codec = StreamCodec(iface)
        used = before - gc.mem_free()
        self.assertEqual(len(codec.report), 64)
        self.assertTrue(used < 1024)
        print("WARD codec object + private report allocation: %d bytes" % used)


if __name__ == "__main__":
    unittest.main()
