# flake8: noqa: F403,F405
from common import *  # isort:skip

import unittest

if not utils.BITCOIN_ONLY:

    from ethereum_common import *

    from apps.ethereum.clear_signing import (
        Array,
        Atomic,
        CalldataReader,
        DirtyAddress,
        Dynamic,
        NonCanonicalLayout,
        OutOfBounds,
        Tuple,
        ValueOverflow,
        parse_address,
        parse_bool,
        parse_bytes,
        parse_bytes32,
        parse_string,
        parse_uint24,
        parse_uint160,
        parse_uint256,
    )

# We use these to pad bytes we are trying to parse left and right
# so that we don't always start parsing from offset 0 which is a special case
FIVE_RANDOM_BYTES = b"\x1a\xf2\x03\x99\x10"
SEVEN_RANDOM_BYTES = b"\xb2^\xa7\x064\x05\x01"


def to_bytes(v: int) -> bytes:
    return v.to_bytes(32, "big")


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumClearSigning(unittest.TestCase):
    def test_address_parsing_valid(self):
        addr_hex = "d8da6bf26964af9d7eed9e03e53415d37aa96045"
        addr_bytes = unhexlify(addr_hex)

        valid_payload = b"\x00" * 12 + addr_bytes
        data = memoryview(valid_payload)

        atomic_addr = Atomic(parse_address)
        parsed, consumed = atomic_addr.parse(CalldataReader(data), 0)

        assert parsed == addr_bytes
        assert consumed == 32

    def test_address_parsing_invalid_padding(self):
        addr_hex = "d8da6bf26964af9d7eed9e03e53415d37aa96045"
        addr_bytes = unhexlify(addr_hex)

        invalid_payload = b"\x01" + b"\x00" * 11 + addr_bytes  # dirty padding
        data = memoryview(invalid_payload)

        atomic_addr = Atomic(parse_address)

        with self.assertRaises(DirtyAddress):
            atomic_addr.parse(CalldataReader(data), 0)

    def test_address_parsing_insufficient_data(self):
        short_data = memoryview(b"\x00" * 20)  # Only 20 bytes provided
        atomic_addr = Atomic(parse_address)

        with self.assertRaises(OutOfBounds):
            atomic_addr.parse(CalldataReader(short_data), 0)

    def test_uint24_parsing(self):
        atomic_uint24 = Atomic(parse_uint24)

        val_int = 1_000_000  # fits in 24 bits
        data = memoryview(FIVE_RANDOM_BYTES + to_bytes(val_int) + SEVEN_RANDOM_BYTES)
        parsed, consumed = atomic_uint24.parse(
            CalldataReader(data), len(FIVE_RANDOM_BYTES)
        )
        self.assertEqual(parsed, val_int)
        self.assertEqual(consumed, 32)

        invalid_val = 2**24
        invalid_data = memoryview(
            FIVE_RANDOM_BYTES + to_bytes(invalid_val) + SEVEN_RANDOM_BYTES
        )
        with self.assertRaises(ValueOverflow):
            atomic_uint24.parse(CalldataReader(invalid_data), len(FIVE_RANDOM_BYTES))

    def test_uint160_parsing(self):
        atomic_uint160 = Atomic(parse_uint160)

        val_int = 2**159 + 5  # fits in 160 bits
        data = memoryview(SEVEN_RANDOM_BYTES + to_bytes(val_int) + FIVE_RANDOM_BYTES)
        parsed, consumed = atomic_uint160.parse(
            CalldataReader(data), len(SEVEN_RANDOM_BYTES)
        )
        self.assertEqual(parsed, val_int)
        self.assertEqual(consumed, 32)

        invalid_val = 2**160
        invalid_data = memoryview(
            SEVEN_RANDOM_BYTES + to_bytes(invalid_val) + FIVE_RANDOM_BYTES
        )
        with self.assertRaises(ValueOverflow):
            atomic_uint160.parse(CalldataReader(invalid_data), len(SEVEN_RANDOM_BYTES))

    def test_bool_parsing(self):
        atomic_bool = Atomic(parse_bool)

        data_true = memoryview(FIVE_RANDOM_BYTES + to_bytes(1) + SEVEN_RANDOM_BYTES)
        parsed, consumed = atomic_bool.parse(
            CalldataReader(data_true), len(FIVE_RANDOM_BYTES)
        )
        self.assertEqual(parsed, True)
        self.assertEqual(consumed, 32)

        data_false = memoryview(SEVEN_RANDOM_BYTES + to_bytes(0) + FIVE_RANDOM_BYTES)
        parsed, consumed = atomic_bool.parse(
            CalldataReader(data_false), len(SEVEN_RANDOM_BYTES)
        )
        self.assertEqual(parsed, False)
        self.assertEqual(consumed, 32)

        invalid_data = memoryview(FIVE_RANDOM_BYTES + to_bytes(2) + SEVEN_RANDOM_BYTES)
        with self.assertRaises(ValueOverflow):
            atomic_bool.parse(CalldataReader(invalid_data), len(FIVE_RANDOM_BYTES))

    def test_uint256_max(self):
        atomic_uint256 = Atomic(parse_uint256)

        # max uint256
        max_uint = (2**256) - 1
        data = memoryview(SEVEN_RANDOM_BYTES + to_bytes(max_uint) + FIVE_RANDOM_BYTES)

        parsed, consumed = atomic_uint256.parse(
            CalldataReader(data), len(SEVEN_RANDOM_BYTES)
        )
        self.assertEqual(parsed, max_uint)
        self.assertEqual(consumed, 32)

    def test_static_struct_valid(self):
        static_struct = Tuple(
            (parse_address, parse_uint160, parse_bool),
            is_dynamic=False,
        )

        addr_bytes = unhexlify("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        u160_val = 2**160 - 1
        bool_val = 1

        # construct the payload
        payload = (
            b"\x00" * (32 - 20) + addr_bytes + to_bytes(u160_val) + to_bytes(bool_val)
        )
        data = memoryview(FIVE_RANDOM_BYTES + payload + SEVEN_RANDOM_BYTES)

        parsed, consumed = static_struct.parse(
            CalldataReader(data), len(FIVE_RANDOM_BYTES)
        )

        self.assertEqual(parsed, (addr_bytes, u160_val, True))
        self.assertEqual(consumed, 96)

    def test_static_struct_uint160_overflow(self):
        static_struct = Tuple(
            (parse_address, parse_uint160, parse_bool),
            is_dynamic=False,
        )

        addr_bytes = unhexlify("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        overflow_u160 = 2**160
        bool_val = 1

        payload = (
            b"\x00" * (32 - 20)
            + addr_bytes
            + to_bytes(overflow_u160)
            + to_bytes(bool_val)
        )
        data = memoryview(FIVE_RANDOM_BYTES + payload + SEVEN_RANDOM_BYTES)

        with self.assertRaises(ValueOverflow):
            static_struct.parse(CalldataReader(data), len(FIVE_RANDOM_BYTES))

    def test_dynamic_struct_valid(self):
        dynamic_struct = Tuple((parse_address, parse_string), is_dynamic=True)

        addr = unhexlify("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        # left padded with zeroes
        addr_bytes = b"\x00" * (32 - 20) + addr

        text = "Hello World!"
        assert len(text) < 32  # could also be more, but then padding would be different
        # right padded with zeroes
        text_bytes = text.encode("utf-8") + b"\x00" * (32 - len(text))

        struct_payload = (
            addr_bytes
            + to_bytes(64)  # pointer to text
            + to_bytes(len(text))  # text length
            + text_bytes
        )

        struct_pointer = (
            len(SEVEN_RANDOM_BYTES) + 32 + len(FIVE_RANDOM_BYTES)
        )  # initial offset + pointer size + actual payload offset
        struct_pointer_bytes = to_bytes(struct_pointer)

        data = memoryview(
            SEVEN_RANDOM_BYTES
            + struct_pointer_bytes
            + FIVE_RANDOM_BYTES
            + struct_payload
        )

        parsed, consumed = dynamic_struct.parse(
            CalldataReader(data), len(SEVEN_RANDOM_BYTES)
        )

        self.assertEqual(parsed, (addr, text))
        self.assertEqual(consumed, 32)  # only the initial pointer is consumed

    def test_dynamic_struct_out_of_bounds(self):
        dynamic_struct = Tuple((parse_uint256,), is_dynamic=True)

        # pointer says struct starts at byte 1000, but data is only 32 bytes long
        payload = to_bytes(1000)
        data = memoryview(payload)

        with self.assertRaises(OutOfBounds):
            dynamic_struct.parse(CalldataReader(data), 0)

    def test_array_of_addresses_valid(self):
        address_array_parser = Array(Atomic(parse_address))

        addr1 = unhexlify("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        addr1_bytes = b"\x00" * (32 - 20) + addr1
        addr2 = unhexlify("71c7656ec7ab88b098defb751b7401b5f6d8976f")
        addr2_bytes = b"\x00" * (32 - 20) + addr2

        array_length = len([addr1, addr2])

        array_pointer = (
            len(FIVE_RANDOM_BYTES) + 32
        )  # absolute position of body in raw_data
        payload = (
            to_bytes(array_pointer)
            + to_bytes(array_length)
            + (addr1_bytes)
            + (addr2_bytes)
        )
        data = memoryview(FIVE_RANDOM_BYTES + payload + SEVEN_RANDOM_BYTES)

        parsed, consumed = address_array_parser.parse(
            CalldataReader(data), len(FIVE_RANDOM_BYTES)
        )

        self.assertEqual(parsed, [addr1, addr2])
        self.assertEqual(consumed, 32)

    def test_array_of_addresses_with_dirty_element(self):
        address_array_parser = Array(Atomic(parse_address))

        addr_valid_bytes = b"\x00" * 12 + unhexlify(
            "d8da6bf26964af9d7eed9e03e53415d37aa96045"
        )
        addr_dirty_bytes = (
            b"\x01"
            + b"\x00" * 11
            + unhexlify("71c7656ec7ab88b098defb751b7401b5f6d8976f")
        )

        payload = (
            to_bytes(32)  # pointer
            + to_bytes(2)  # size
            + addr_valid_bytes
            + addr_dirty_bytes
        )
        data = memoryview(payload)

        with self.assertRaises(DirtyAddress):
            address_array_parser.parse(CalldataReader(data), 0)

    def test_array_of_dynamic_structs(self):
        array_parser = Array(
            Tuple(
                (parse_address, parse_string),
                # Note: dynamic structs that sit inside arrays behave as static structs
                is_dynamic=False,
            )
        )

        addr1 = unhexlify("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        addr2 = unhexlify("71c7656ec7ab88b098defb751b7401b5f6d8976f")
        text1 = "Hello first world!"
        text2 = "Hello second world!"

        def pack_struct(addr, text):
            addr_bytes = b"\x00" * (32 - 20) + addr
            assert len(text) < 32  # just to simplify padding code below
            text_bytes = text.encode("utf-8") + b"\x00" * (32 - len(text))
            text_pointer = 64  # relative to struct start
            return (
                addr_bytes + to_bytes(text_pointer) + to_bytes(len(text)) + text_bytes
            )

        struct0_payload = pack_struct(addr1, text1)
        struct1_payload = pack_struct(addr2, text2)

        array_pointer = 32

        array_len = len([struct0_payload, struct1_payload])

        struct0_pointer = 64
        struct1_pointer = 192

        payload = (
            to_bytes(array_pointer)
            + to_bytes(array_len)
            + to_bytes(struct0_pointer)
            + to_bytes(struct1_pointer)
            + struct0_payload
            + struct1_payload
        )

        data = memoryview(payload)

        parsed, consumed = array_parser.parse(CalldataReader(data), 0)

        self.assertEqual(parsed, [(addr1, text1), (addr2, text2)])
        self.assertEqual(consumed, 32)

    def test_bytes32_parsing(self):
        atomic_bytes32 = Atomic(parse_bytes32)

        b32 = bytes(range(32))
        data = memoryview(FIVE_RANDOM_BYTES + b32 + SEVEN_RANDOM_BYTES)
        parsed, consumed = atomic_bytes32.parse(
            CalldataReader(data), len(FIVE_RANDOM_BYTES)
        )
        self.assertEqual(parsed, b32)
        self.assertEqual(consumed, 32)

        with self.assertRaises(OutOfBounds):
            atomic_bytes32.parse(CalldataReader(memoryview(b"\x00" * 20)), 0)

    def test_array_of_arrays_of_bytes32(self):
        # bytes32[][] = [[b0, b1], [b2]]
        nested_array_parser = Array(Array(Atomic(parse_bytes32)))

        b0 = bytes(range(0, 32))
        b1 = bytes(range(32, 64))
        b2 = bytes(range(64, 96))

        # ABI layout (offsets are absolute positions within raw_data):
        #   [7]:   pointer slot → outer body at 7+32 = 39
        #   [39]:  outer length = 2
        #   [71]:  rel. offset to inner[0] from heads base (=71): 135-71 = 64
        #   [103]: rel. offset to inner[1] from heads base (=71): 231-71 = 160
        #   [135]: inner[0] length = 2
        #   [167]: inner[0][0] = b0
        #   [199]: inner[0][1] = b1
        #   [231]: inner[1] length = 1
        #   [263]: inner[1][0] = b2
        payload = (
            to_bytes(
                len(SEVEN_RANDOM_BYTES) + 32
            )  # pointer: absolute raw_data pos of outer body
            + to_bytes(2)  # outer length
            + to_bytes(64)  # rel. offset → inner[0]
            + to_bytes(160)  # rel. offset → inner[1]
            + to_bytes(2)  # inner[0] length
            + b0
            + b1
            + to_bytes(1)  # inner[1] length
            + b2
        )
        data = memoryview(SEVEN_RANDOM_BYTES + payload + FIVE_RANDOM_BYTES)

        parsed, consumed = nested_array_parser.parse(
            CalldataReader(data), len(SEVEN_RANDOM_BYTES)
        )
        self.assertEqual(parsed, [[b0, b1], [b2]])
        self.assertEqual(consumed, 32)

    def test_array_of_arrays_out_of_bounds(self):
        nested_array_parser = Array(Array(Atomic(parse_bytes32)))

        # outer array pointer points beyond the data
        payload = to_bytes(9999)
        with self.assertRaises(OutOfBounds):
            nested_array_parser.parse(CalldataReader(memoryview(payload)), 0)

        # inner array length overruns the data — test both sides of the border

        # border valid: inner[0] length = 0 → empty inner array, parses as [[]]
        # pointer = len(SEVEN_RANDOM_BYTES) + 32 = absolute raw_data pos of outer body
        payload_ok = (
            to_bytes(len(SEVEN_RANDOM_BYTES) + 32)  # pointer to outer body
            + to_bytes(1)  # outer length = 1
            + to_bytes(32)  # rel. offset to inner[0] from heads base
            + to_bytes(0)  # inner[0] length = 0 → empty
        )
        data = memoryview(SEVEN_RANDOM_BYTES + payload_ok + FIVE_RANDOM_BYTES)
        parsed, consumed = nested_array_parser.parse(
            CalldataReader(data), len(SEVEN_RANDOM_BYTES)
        )
        self.assertEqual(parsed, [[]])
        self.assertEqual(consumed, 32)

        # border invalid: inner[0] length = 1 but no element data follows
        payload_fail = (
            to_bytes(32)  # pointer to outer body (no prefix, absolute pos = 32)
            + to_bytes(1)  # outer length = 1
            + to_bytes(32)  # rel. offset to inner[0] from heads base
            + to_bytes(1)  # inner[0] length = 1 — one element claimed but no data
        )
        with self.assertRaises(OutOfBounds):
            nested_array_parser.parse(CalldataReader(memoryview(payload_fail)), 0)

    # --- Step 2: non-canonical (non-forward-streamable) layouts are rejected ---

    def _parse_sequence(self, definitions, data, start=0):
        # Parse top-level params the way DisplayFormat.parse_calldata does:
        # one shared reader, each definition parsed at an increasing offset.
        reader = CalldataReader(memoryview(data))
        offset = start
        parsed = []
        for definition in definitions:
            value, consumed = definition.parse(reader, offset)
            parsed.append(value)
            offset += consumed
        return parsed

    def test_noncanonical_reversed_dynamic_tails(self):
        # Two `bytes` params whose tails are laid out in reverse order. A
        # random-access decoder accepts this, but it cannot be served by a
        # forward-only stream, so we reject it.
        buf = bytearray(192)

        def w(off, val):
            buf[off : off + 32] = to_bytes(val)

        w(0, 128)  # param0 -> blob at offset 128
        w(32, 64)  # param1 -> blob at offset 64 (before param0's tail!)
        w(64, 2)
        buf[96:98] = b"\xaa\xbb"  # param1's blob
        w(128, 2)
        buf[160:162] = b"\xcc\xdd"  # param0's blob

        with self.assertRaises(NonCanonicalLayout):
            self._parse_sequence(
                (Dynamic(parse_bytes), Dynamic(parse_bytes)), bytes(buf)
            )

    def test_canonical_adjacent_dynamic_ok(self):
        # Boundary case: param1's tail starts exactly where param0's tail ends.
        # `seek_forward` allows target == frontier, so this must NOT be rejected.
        buf = bytearray(192)

        def w(off, val):
            buf[off : off + 32] = to_bytes(val)

        w(0, 64)  # param0 -> blob0 at offset 64
        w(64, 32)
        buf[96:128] = bytes(range(32))  # blob0 data, ends exactly at 128
        w(32, 128)  # param1 -> blob1 at offset 128 (== frontier)
        w(128, 2)
        buf[160:162] = b"\x01\x02"

        parsed = self._parse_sequence(
            (Dynamic(parse_bytes), Dynamic(parse_bytes)), bytes(buf)
        )
        self.assertEqual(parsed, [bytes(range(32)), b"\x01\x02"])

    def test_noncanonical_dynamic_struct_backward_pointer(self):
        # A dynamic struct whose pointer points backward into already-read data.
        dynamic_struct = Tuple((parse_uint256,), is_dynamic=True)
        data = memoryview(SEVEN_RANDOM_BYTES + to_bytes(0) + to_bytes(123))
        with self.assertRaises(NonCanonicalLayout):
            dynamic_struct.parse(CalldataReader(data), len(SEVEN_RANDOM_BYTES))

    def test_noncanonical_array_elements_out_of_order(self):
        # Array of dynamic structs whose element pointers are in reverse order:
        # element 0 points past element 1's body, so reading element 1 would
        # require seeking backward.
        array_parser = Array(Tuple((parse_address, parse_string), is_dynamic=False))

        addr1 = unhexlify("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        addr2 = unhexlify("71c7656ec7ab88b098defb751b7401b5f6d8976f")

        def pack_struct(addr, text):
            addr_bytes = b"\x00" * (32 - 20) + addr
            text_bytes = text.encode("utf-8") + b"\x00" * (32 - len(text))
            return addr_bytes + to_bytes(64) + to_bytes(len(text)) + text_bytes

        s0 = pack_struct(addr1, "first")
        s1 = pack_struct(addr2, "second")
        payload = (
            to_bytes(32)  # array pointer
            + to_bytes(2)  # array length
            + to_bytes(192)  # element 0 -> body+192 (the later struct)
            + to_bytes(64)  # element 1 -> body+64 (the earlier struct)
            + s0
            + s1
        )
        with self.assertRaises(NonCanonicalLayout):
            array_parser.parse(CalldataReader(memoryview(payload)), 0)


if __name__ == "__main__":
    unittest.main()
