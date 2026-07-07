# flake8: noqa: F403,F405
from common import *  # isort:skip

import unittest

if not utils.BITCOIN_ONLY:

    from ethereum_common import *
    from trezor.enums import EthereumERC7730FieldFormatterType as FT
    from trezor.messages import (
        EthereumERC7730EnumEntry,
        EthereumERC7730FieldInfo,
        EthereumERC7730Path,
    )

    from apps.ethereum import clear_signing_definitions
    from apps.ethereum.clear_signing import (
        AddressNameFormatter,
        Array,
        Atomic,
        CalldataFormatter,
        ContainerPath,
        DateFormatter,
        DirtyAddress,
        DisplayFormat,
        DynamicLeaf,
        EnumFormatter,
        FieldDefinition,
        InvalidFormatDefinition,
        OutOfBounds,
        RawFormatter,
        TokenAmountFormatter,
        Tuple,
        ValueOverflow,
        _expand_calldata_field,
        _format_field_value,
        make_fixed_bytes_parser,
        make_int_parser,
        make_uint_parser,
        parse_address,
        parse_bool,
        parse_bytes,
        parse_string,
        parse_uint256,
    )

    parse_bytes4 = make_fixed_bytes_parser(4)
    parse_bytes8 = make_fixed_bytes_parser(8)
    parse_bytes16 = make_fixed_bytes_parser(16)
    parse_bytes20 = make_fixed_bytes_parser(20)
    parse_bytes32 = make_fixed_bytes_parser(32)
    parse_int160 = make_int_parser(160)
    parse_uint24 = make_uint_parser(24)
    parse_uint160 = make_uint_parser(160)

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
        addr_bytes = bytes.fromhex(addr_hex)

        valid_payload = b"\x00" * 12 + addr_bytes
        data = memoryview(valid_payload)

        atomic_addr = Atomic(parse_address)
        parsed, consumed = atomic_addr.parse(data, 0)

        assert parsed == addr_bytes
        assert consumed == 32

    def test_address_parsing_invalid_padding(self):
        addr_hex = "d8da6bf26964af9d7eed9e03e53415d37aa96045"
        addr_bytes = bytes.fromhex(addr_hex)

        invalid_payload = b"\x01" + b"\x00" * 11 + addr_bytes  # dirty padding
        data = memoryview(invalid_payload)

        atomic_addr = Atomic(parse_address)

        with self.assertRaises(DirtyAddress):
            atomic_addr.parse(data, 0)

    def test_address_parsing_insufficient_data(self):
        short_data = memoryview(b"\x00" * 20)  # Only 20 bytes provided
        atomic_addr = Atomic(parse_address)

        with self.assertRaises(OutOfBounds):
            atomic_addr.parse(short_data, 0)

    def test_uint24_parsing(self):
        atomic_uint24 = Atomic(parse_uint24)

        val_int = 1_000_000  # fits in 24 bits
        data = memoryview(FIVE_RANDOM_BYTES + to_bytes(val_int) + SEVEN_RANDOM_BYTES)
        parsed, consumed = atomic_uint24.parse(data, len(FIVE_RANDOM_BYTES))
        self.assertEqual(parsed, val_int)
        self.assertEqual(consumed, 32)

        invalid_val = 2**24
        invalid_data = memoryview(
            FIVE_RANDOM_BYTES + to_bytes(invalid_val) + SEVEN_RANDOM_BYTES
        )
        with self.assertRaises(ValueOverflow):
            atomic_uint24.parse(invalid_data, len(FIVE_RANDOM_BYTES))

    def test_uint160_parsing(self):
        atomic_uint160 = Atomic(parse_uint160)

        val_int = 2**159 + 5  # fits in 160 bits
        data = memoryview(SEVEN_RANDOM_BYTES + to_bytes(val_int) + FIVE_RANDOM_BYTES)
        parsed, consumed = atomic_uint160.parse(data, len(SEVEN_RANDOM_BYTES))
        self.assertEqual(parsed, val_int)
        self.assertEqual(consumed, 32)

        invalid_val = 2**160
        invalid_data = memoryview(
            SEVEN_RANDOM_BYTES + to_bytes(invalid_val) + FIVE_RANDOM_BYTES
        )
        with self.assertRaises(ValueOverflow):
            atomic_uint160.parse(invalid_data, len(SEVEN_RANDOM_BYTES))

    def test_bool_parsing(self):
        atomic_bool = Atomic(parse_bool)

        data_true = memoryview(FIVE_RANDOM_BYTES + to_bytes(1) + SEVEN_RANDOM_BYTES)
        parsed, consumed = atomic_bool.parse(data_true, len(FIVE_RANDOM_BYTES))
        self.assertEqual(parsed, True)
        self.assertEqual(consumed, 32)

        data_false = memoryview(SEVEN_RANDOM_BYTES + to_bytes(0) + FIVE_RANDOM_BYTES)
        parsed, consumed = atomic_bool.parse(data_false, len(SEVEN_RANDOM_BYTES))
        self.assertEqual(parsed, False)
        self.assertEqual(consumed, 32)

        invalid_data = memoryview(FIVE_RANDOM_BYTES + to_bytes(2) + SEVEN_RANDOM_BYTES)
        with self.assertRaises(ValueOverflow):
            atomic_bool.parse(invalid_data, len(FIVE_RANDOM_BYTES))

    def test_uint256_max(self):
        atomic_uint256 = Atomic(parse_uint256)

        # max uint256
        max_uint = (2**256) - 1
        data = memoryview(SEVEN_RANDOM_BYTES + to_bytes(max_uint) + FIVE_RANDOM_BYTES)

        parsed, consumed = atomic_uint256.parse(data, len(SEVEN_RANDOM_BYTES))
        self.assertEqual(parsed, max_uint)
        self.assertEqual(consumed, 32)

    def test_static_struct_valid(self):
        static_struct = Tuple(
            (parse_address, parse_uint160, parse_bool),
            is_dynamic=False,
        )

        addr_bytes = bytes.fromhex("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        u160_val = 2**160 - 1
        bool_val = 1

        # construct the payload
        payload = (
            b"\x00" * (32 - 20) + addr_bytes + to_bytes(u160_val) + to_bytes(bool_val)
        )
        data = memoryview(FIVE_RANDOM_BYTES + payload + SEVEN_RANDOM_BYTES)

        parsed, consumed = static_struct.parse(data, len(FIVE_RANDOM_BYTES))

        self.assertEqual(parsed, (addr_bytes, u160_val, True))
        self.assertEqual(consumed, 96)

    def test_static_struct_uint160_overflow(self):
        static_struct = Tuple(
            (parse_address, parse_uint160, parse_bool),
            is_dynamic=False,
        )

        addr_bytes = bytes.fromhex("d8da6bf26964af9d7eed9e03e53415d37aa96045")
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
            static_struct.parse(data, len(FIVE_RANDOM_BYTES))

    def test_dynamic_struct_valid(self):
        dynamic_struct = Tuple((parse_address, parse_string), is_dynamic=True)

        addr = bytes.fromhex("d8da6bf26964af9d7eed9e03e53415d37aa96045")
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

        parsed, consumed = dynamic_struct.parse(data, len(SEVEN_RANDOM_BYTES))

        self.assertEqual(parsed, (addr, text))
        self.assertEqual(consumed, 32)  # only the initial pointer is consumed

    def test_dynamic_struct_out_of_bounds(self):
        dynamic_struct = Tuple((parse_uint256,), is_dynamic=True)

        # pointer says struct starts at byte 1000, but data is only 32 bytes long
        payload = to_bytes(1000)
        data = memoryview(payload)

        with self.assertRaises(OutOfBounds):
            dynamic_struct.parse(data, 0)

    def test_array_of_addresses_valid(self):
        address_array_parser = Array(Atomic(parse_address))

        addr1 = bytes.fromhex("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        addr1_bytes = b"\x00" * (32 - 20) + addr1
        addr2 = bytes.fromhex("71c7656ec7ab88b098defb751b7401b5f6d8976f")
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

        parsed, consumed = address_array_parser.parse(data, len(FIVE_RANDOM_BYTES))

        self.assertEqual(parsed, [addr1, addr2])
        self.assertEqual(consumed, 32)

    def test_array_of_addresses_with_dirty_element(self):
        address_array_parser = Array(Atomic(parse_address))

        addr_valid_bytes = b"\x00" * 12 + bytes.fromhex(
            "d8da6bf26964af9d7eed9e03e53415d37aa96045"
        )
        addr_dirty_bytes = (
            b"\x01"
            + b"\x00" * 11
            + bytes.fromhex("71c7656ec7ab88b098defb751b7401b5f6d8976f")
        )

        payload = (
            to_bytes(32)  # pointer
            + to_bytes(2)  # size
            + addr_valid_bytes
            + addr_dirty_bytes
        )
        data = memoryview(payload)

        with self.assertRaises(DirtyAddress):
            address_array_parser.parse(data, 0)

    def test_array_of_dynamic_structs(self):
        array_parser = Array(
            Tuple(
                (parse_address, parse_string),
                # the `string` field makes the struct a dynamic type, so the
                # array encodes its elements via offset heads
                is_dynamic=True,
            )
        )

        addr1 = bytes.fromhex("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        addr2 = bytes.fromhex("71c7656ec7ab88b098defb751b7401b5f6d8976f")
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

        parsed, consumed = array_parser.parse(data, 0)

        self.assertEqual(parsed, [(addr1, text1), (addr2, text2)])
        self.assertEqual(consumed, 32)

    def test_array_of_static_structs(self):
        # (address,address,uint256)[]: the struct has no dynamic fields, so it
        # is a static type - array elements are encoded IN PLACE right after
        # the length word, at a stride of the struct size (96 bytes), with no
        # offset heads at all.
        array_parser = Array(
            Tuple(
                (parse_address, parse_address, parse_uint256),
                is_dynamic=False,
            )
        )

        addr1 = bytes.fromhex("6666666666666666666666666666666666666666")
        addr2 = bytes.fromhex("7777777777777777777777777777777777777777")
        addr3 = bytes.fromhex("8888888888888888888888888888888888888888")
        addr4 = bytes.fromhex("9999999999999999999999999999999999999999")

        def pad_addr(addr):
            return b"\x00" * (32 - 20) + addr

        array_pointer = len(FIVE_RANDOM_BYTES) + 32  # absolute pos of array body
        payload = (
            to_bytes(array_pointer)
            + to_bytes(2)  # element count; elements follow in place
            + pad_addr(addr1)  # element 0
            + pad_addr(addr2)
            + to_bytes(6000000)
            + pad_addr(addr3)  # element 1
            + pad_addr(addr4)
            + to_bytes(1500000)
        )
        data = memoryview(FIVE_RANDOM_BYTES + payload + SEVEN_RANDOM_BYTES)

        parsed, consumed = array_parser.parse(data, len(FIVE_RANDOM_BYTES))

        self.assertEqual(parsed, [(addr1, addr2, 6000000), (addr3, addr4, 1500000)])
        self.assertEqual(consumed, 32)  # only the array's own offset head

        # count claims two elements but only one is present: the heads area
        # (2 * 96 bytes) fails the bounds pre-check
        truncated = (
            to_bytes(32)  # pointer to array body (absolute pos, no prefix)
            + to_bytes(2)
            + pad_addr(addr1)
            + pad_addr(addr2)
            + to_bytes(6000000)
        )
        with self.assertRaises(OutOfBounds):
            array_parser.parse(memoryview(truncated), 0)

    def test_empty_tuple_rejected(self):
        # Zero-field structs don't exist in Solidity. A static one would have
        # head_size == 0, and inside an Array that zero stride would defeat
        # the heads bounds pre-check (array_length * 0) and let an
        # attacker-controlled length word drive an unbounded parse loop.
        with self.assertRaises(InvalidFormatDefinition):
            Tuple((), is_dynamic=False)
        with self.assertRaises(InvalidFormatDefinition):
            Tuple((), is_dynamic=True)

    def test_bytes32_parsing(self):
        atomic_bytes32 = Atomic(parse_bytes32)

        b32 = bytes(range(32))
        data = memoryview(FIVE_RANDOM_BYTES + b32 + SEVEN_RANDOM_BYTES)
        parsed, consumed = atomic_bytes32.parse(data, len(FIVE_RANDOM_BYTES))
        self.assertEqual(parsed, b32)
        self.assertEqual(consumed, 32)

        with self.assertRaises(OutOfBounds):
            atomic_bytes32.parse(memoryview(b"\x00" * 20), 0)

    def test_fixed_bytes_parsing(self):
        # bytesN is left-aligned in the word: value first, zero padding after
        for parser, width in (
            (parse_bytes4, 4),
            (parse_bytes8, 8),
            (parse_bytes16, 16),
            (parse_bytes20, 20),
        ):
            atomic = Atomic(parser)

            value = bytes(range(1, width + 1))
            word = value + b"\x00" * (32 - width)
            data = memoryview(FIVE_RANDOM_BYTES + word + SEVEN_RANDOM_BYTES)
            parsed, consumed = atomic.parse(data, len(FIVE_RANDOM_BYTES))
            self.assertEqual(parsed, value)
            self.assertEqual(consumed, 32)

            # dirty right padding (a stray bit just past the value)
            dirty_word = value + b"\x01" + b"\x00" * (32 - width - 1)
            dirty_data = memoryview(FIVE_RANDOM_BYTES + dirty_word + SEVEN_RANDOM_BYTES)
            with self.assertRaises(ValueOverflow):
                atomic.parse(dirty_data, len(FIVE_RANDOM_BYTES))

            with self.assertRaises(OutOfBounds):
                atomic.parse(memoryview(b"\x00" * 20), 0)

    def test_int160_parsing(self):
        atomic_int160 = Atomic(parse_int160)

        def signed_word(v: int) -> bytes:
            return (v & ((1 << 256) - 1)).to_bytes(32, "big")

        for val in (0, 1, -1, 2**159 - 1, -(2**159), -123456789):
            data = memoryview(SEVEN_RANDOM_BYTES + signed_word(val) + FIVE_RANDOM_BYTES)
            parsed, consumed = atomic_int160.parse(data, len(SEVEN_RANDOM_BYTES))
            self.assertEqual(parsed, val)
            self.assertEqual(consumed, 32)

        # out of int160 range (both directions), including a value with
        # dirty sign-extension bits
        for invalid in (2**159, -(2**159) - 1, 2**200):
            invalid_data = memoryview(
                SEVEN_RANDOM_BYTES + signed_word(invalid) + FIVE_RANDOM_BYTES
            )
            with self.assertRaises(ValueOverflow):
                atomic_int160.parse(invalid_data, len(SEVEN_RANDOM_BYTES))

        with self.assertRaises(OutOfBounds):
            atomic_int160.parse(memoryview(b"\x00" * 20), 0)

    def test_int256_parsing(self):
        # int256 is the full word width, so every bit pattern is in range
        # (no sign-extension padding to check).
        atomic_int256 = Atomic(make_int_parser(256))

        def signed_word(v: int) -> bytes:
            return (v & ((1 << 256) - 1)).to_bytes(32, "big")

        for val in (0, 1, -1, 2**255 - 1, -(2**255), -123456789):
            data = memoryview(SEVEN_RANDOM_BYTES + signed_word(val) + FIVE_RANDOM_BYTES)
            parsed, consumed = atomic_int256.parse(data, len(SEVEN_RANDOM_BYTES))
            self.assertEqual(parsed, val)
            self.assertEqual(consumed, 32)

        with self.assertRaises(OutOfBounds):
            atomic_int256.parse(memoryview(b"\x00" * 20), 0)

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

        parsed, consumed = nested_array_parser.parse(data, len(SEVEN_RANDOM_BYTES))
        self.assertEqual(parsed, [[b0, b1], [b2]])
        self.assertEqual(consumed, 32)

    def test_array_of_arrays_out_of_bounds(self):
        nested_array_parser = Array(Array(Atomic(parse_bytes32)))

        # outer array pointer points beyond the data
        payload = to_bytes(9999)
        with self.assertRaises(OutOfBounds):
            nested_array_parser.parse(memoryview(payload), 0)

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
        parsed, consumed = nested_array_parser.parse(data, len(SEVEN_RANDOM_BYTES))
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
            nested_array_parser.parse(memoryview(payload_fail), 0)

    # --- Field formatters ---

    def test_raw_formatter(self):
        fmt = RawFormatter()

        # int -> decimal, including a full-width uint256 (no float rounding / sci-notation)
        big = 2**256 - 1
        for value, expected in (
            (0, "0"),
            (291, "291"),
            (big, str(big)),
        ):
            formatted, token, addr = await_result(fmt.format(value, None, None, None))
            self.assertEqual(formatted, expected)
            self.assertIsNone(token)
            self.assertIsNone(addr)

        # string -> passed through unchanged
        formatted, _, _ = await_result(fmt.format("Trezor", None, None, None))
        self.assertEqual(formatted, "Trezor")

        # bytes -> hex-encoded string
        formatted, _, _ = await_result(
            fmt.format(b"\x12\x34\x56\x78\x9a", None, None, None)
        )
        self.assertEqual(formatted, "123456789a")

        # None -> None
        formatted, _, _ = await_result(fmt.format(None, None, None, None))
        self.assertIsNone(formatted)

    def test_date_formatter(self):
        fmt = DateFormatter()

        # unix timestamp (seconds) -> human-readable date
        formatted, token, addr = await_result(fmt.format(1616051824, None, None, None))
        self.assertEqual(formatted, "2021-03-18 07:17:04")
        self.assertIsNone(token)
        self.assertIsNone(addr)

        formatted, _, _ = await_result(fmt.format(0, None, None, None))
        self.assertEqual(formatted, "1970-01-01 00:00:00")

        # None -> None
        formatted, _, _ = await_result(fmt.format(None, None, None, None))
        self.assertIsNone(formatted)

        # a sliced word, e.g. `goodUntil.[-4:]`: big-endian seconds
        formatted, _, _ = await_result(
            fmt.format((1616051824).to_bytes(4, "big"), None, None, None)
        )
        self.assertEqual(formatted, "2021-03-18 07:17:04")

        # non-timestamp value is rejected
        with self.assertRaises(InvalidFormatDefinition):
            await_result(fmt.format("not-a-timestamp", None, None, None))

    def test_from_proto_raw_date_dispatch(self):
        # End-to-end from a proto enum value to a rendered string. `from_proto`
        # maps the wire integer (FORMATTER_RAW=4 / FORMATTER_DATE=5) to a
        # formatter class.
        raw_info = EthereumERC7730FieldInfo(
            path=EthereumERC7730Path(path=[0]),
            label="Field",
            formatter=FT.FORMATTER_RAW,
        )
        raw_fmt = FieldDefinition.from_proto(raw_info).get_formatter()
        self.assertIsInstance(raw_fmt, RawFormatter)
        formatted, _, _ = await_result(raw_fmt.format(42, None, None, None))
        self.assertEqual(formatted, "42")

        date_info = EthereumERC7730FieldInfo(
            path=EthereumERC7730Path(path=[0]),
            label="Field",
            formatter=FT.FORMATTER_DATE,
        )
        date_fmt = FieldDefinition.from_proto(date_info).get_formatter()
        self.assertIsInstance(date_fmt, DateFormatter)
        formatted, _, _ = await_result(date_fmt.format(1616051824, None, None, None))
        self.assertEqual(formatted, "2021-03-18 07:17:04")

    # --- enum formatter ---

    def test_enum_formatter(self):
        # ERC-7730 `enum` format: an ABI-registered enum for interestRateMode
        # in Aave's supply/borrow calls.
        fmt = EnumFormatter({1: "stable", 2: "variable"})

        formatted, token, addr = await_result(fmt.format(1, None, None, None))
        self.assertEqual(formatted, "stable")
        self.assertIsNone(token)
        self.assertIsNone(addr)

        formatted, _, _ = await_result(fmt.format(2, None, None, None))
        self.assertEqual(formatted, "variable")

        # None -> None
        formatted, _, _ = await_result(fmt.format(None, None, None, None))
        self.assertIsNone(formatted)

        # a key missing from the mapping fails clear signing
        with self.assertRaises(InvalidFormatDefinition):
            await_result(fmt.format(3, None, None, None))

        # non-integer values are rejected
        with self.assertRaises(InvalidFormatDefinition):
            await_result(fmt.format("stable", None, None, None))

        # an enum pointed at an array renders one entry per line
        formatted, _, _ = await_result(
            _format_field_value(fmt, [2, 1], None, None, None)
        )
        self.assertEqual(formatted, "variable\nstable")

    def test_from_proto_enum_dispatch(self):
        info = EthereumERC7730FieldInfo(
            path=EthereumERC7730Path(path=[0]),
            label="Interest rate mode",
            formatter=FT.FORMATTER_ENUM,
            enum_values=[
                EthereumERC7730EnumEntry(key=1, value="stable"),
                EthereumERC7730EnumEntry(key=2, value="variable"),
            ],
        )
        fmt = FieldDefinition.from_proto(info).get_formatter()
        self.assertIsInstance(fmt, EnumFormatter)
        formatted, _, _ = await_result(fmt.format(2, None, None, None))
        self.assertEqual(formatted, "variable")

        # an enum field without its mapping is rejected at decode time
        info = EthereumERC7730FieldInfo(
            path=EthereumERC7730Path(path=[0]),
            label="Interest rate mode",
            formatter=FT.FORMATTER_ENUM,
        )
        with self.assertRaises(InvalidFormatDefinition):
            FieldDefinition.from_proto(info)

    def test_enum_end_to_end(self):
        # Full path: calldata -> parse a `uint8` parameter -> the field renders
        # the mapped display string.
        def make_display_format():
            return DisplayFormat(
                binding_context=None,
                func_sig=b"\x00\x00\x00\x00",
                provider_name=None,
                intent="Test",
                parameter_definitions=[Atomic(make_uint_parser(8))],
                field_definitions=[
                    FieldDefinition(
                        (0,), "Rate mode", EnumFormatter({1: "stable", 2: "variable"})
                    )
                ],
            )

        parameters, fields = await_result(
            make_display_format().parse_calldata(memoryview(to_bytes(2)), None, None)
        )
        self.assertEqual(parameters, [2])
        (label, formatted, _), token, token_address = fields[0]
        self.assertEqual(label, "Rate mode")
        self.assertEqual(formatted, "variable")
        self.assertIsNone(token)
        self.assertIsNone(token_address)

        # a calldata value outside the mapping fails the parse (blind signing)
        with self.assertRaises(InvalidFormatDefinition):
            await_result(
                make_display_format().parse_calldata(
                    memoryview(to_bytes(3)), None, None
                )
            )

    # --- Multi-value fields (a formatter pointed at an array) ---

    def test_multi_value_formats_each_element(self):
        # A formatter pointed at an array formats every element and joins the
        # rendered values with newlines (one value per line).
        fmt = RawFormatter()

        formatted, token, addr = await_result(
            _format_field_value(fmt, [10, 20, 30], None, None, None)
        )
        self.assertEqual(formatted, "10\n20\n30")
        self.assertIsNone(token)
        self.assertIsNone(addr)

        # works for any leaf type the formatter supports
        formatted, _, _ = await_result(
            _format_field_value(fmt, ["alice", "bob"], None, None, None)
        )
        self.assertEqual(formatted, "alice\nbob")

    def test_multi_value_scalar_passthrough(self):
        # A non-list value is formatted directly (no newline wrapping).
        fmt = RawFormatter()
        formatted, _, _ = await_result(_format_field_value(fmt, 42, None, None, None))
        self.assertEqual(formatted, "42")

    def test_multi_value_empty_and_single(self):
        fmt = RawFormatter()

        # empty array renders as an empty string
        formatted, _, _ = await_result(_format_field_value(fmt, [], None, None, None))
        self.assertEqual(formatted, "")

        # a single-element array still renders the element (no trailing newline)
        formatted, _, _ = await_result(_format_field_value(fmt, [7], None, None, None))
        self.assertEqual(formatted, "7")

    def test_multi_value_nested_array_rejected(self):
        # We only render flat arrays. A nested-array element is a `list`, which
        # no formatter accepts, so it cleanly falls back (blind signing) rather
        # than being silently flattened.
        fmt = RawFormatter()
        with self.assertRaises(InvalidFormatDefinition):
            await_result(_format_field_value(fmt, [[1, 2], [3]], None, None, None))

    def test_multi_value_none_element_rejected(self):
        # An element that produces no rendering must not become a blank line.
        fmt = RawFormatter()
        with self.assertRaises(InvalidFormatDefinition):
            await_result(_format_field_value(fmt, [1, None, 3], None, None, None))

    def test_multi_value_address_array(self):
        # The same behaviour with a richer formatter: an array of addresses is
        # rendered as one checksummed (EIP-55) address per line.
        class _Defs:
            network = make_eth_network()

        fmt = AddressNameFormatter()
        addr1 = bytes.fromhex("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        addr2 = bytes.fromhex("71c7656ec7ab88b098defb751b7401b5f6d8976f")

        formatted, _, _ = await_result(
            _format_field_value(fmt, [addr1, addr2], None, _Defs(), None)
        )
        line1, line2 = formatted.split("\n")
        self.assertEqual(
            line1.lower(), "0x" + "d8da6bf26964af9d7eed9e03e53415d37aa96045"
        )
        self.assertEqual(
            line2.lower(), "0x" + "71c7656ec7ab88b098defb751b7401b5f6d8976f"
        )

    def test_multi_value_token_amount(self):
        # Multi-value with TokenAmountFormatter: every element shares the one
        # (constant) token, rendered one amount-per-line.
        token_addr = bytes.fromhex("ae7ab96520de3a18e5e111b5eaab095312d7fe84")

        class _Defs:
            network = make_eth_network()

            def get_token(self, address):
                return make_eth_token(symbol="TST", decimals=6, address=address)

        fmt = TokenAmountFormatter(const_token_address=token_addr)
        formatted, token, addr = await_result(
            _format_field_value(fmt, [1_000_000, 2_000_000], None, _Defs(), None)
        )
        self.assertEqual(formatted, "1 TST\n2 TST")
        self.assertEqual(token.symbol, "TST")
        self.assertEqual(addr, token_addr)

    def test_multi_value_date(self):
        # Multi-value with DateFormatter: a list of timestamps -> one date per line.
        fmt = DateFormatter()
        formatted, token, addr = await_result(
            _format_field_value(fmt, [1616051824, 0], None, None, None)
        )
        self.assertEqual(formatted, "2021-03-18 07:17:04\n1970-01-01 00:00:00")
        self.assertIsNone(token)
        self.assertIsNone(addr)

    def test_multi_value_end_to_end(self):
        # Full path: calldata -> parse a `uint256[]` parameter -> the field path
        # resolves to the whole array -> rendered as one value per line.
        display_format = DisplayFormat(
            binding_context=None,
            func_sig=b"\x00\x00\x00\x00",
            provider_name=None,
            intent="Test",
            parameter_definitions=[Array(Atomic(parse_uint256))],
            field_definitions=[FieldDefinition((0,), "Values", RawFormatter)],
        )

        calldata = (
            to_bytes(32)  # pointer to the array body
            + to_bytes(3)  # array length
            + to_bytes(10)
            + to_bytes(20)
            + to_bytes(30)
        )

        parameters, fields = await_result(
            display_format.parse_calldata(memoryview(calldata), None, None)
        )

        self.assertEqual(parameters, [[10, 20, 30]])
        self.assertEqual(len(fields), 1)
        (label, formatted, _), token, token_address = fields[0]
        self.assertEqual(label, "Values")
        self.assertEqual(formatted, "10\n20\n30")
        self.assertIsNone(token)
        self.assertIsNone(token_address)

    # --- constant (non-calldata) value fields ---

    def test_from_proto_const_value_path(self):
        # A `const_value` path decodes to the literal string — a value source
        # that is not walked from calldata.
        info = EthereumERC7730FieldInfo(
            path=EthereumERC7730Path(const_value="kmgcEURC"),
            label="Share ticker",
            formatter=FT.FORMATTER_RAW,
        )
        field = FieldDefinition.from_proto(info)
        self.assertEqual(field.path, "kmgcEURC")
        self.assertIsInstance(field.get_formatter(), RawFormatter)

    def test_const_value_end_to_end(self):
        # A field bound to a constant renders the literal as-is, without touching
        # calldata (empty params, empty calldata).
        display_format = DisplayFormat(
            binding_context=None,
            func_sig=b"\x00\x00\x00\x00",
            provider_name=None,
            intent="Test",
            parameter_definitions=[],
            field_definitions=[
                FieldDefinition("kmgcEURC", "Share ticker", RawFormatter)
            ],
        )

        parameters, fields = await_result(
            display_format.parse_calldata(memoryview(b""), None, None)
        )

        self.assertEqual(parameters, [])
        self.assertEqual(len(fields), 1)
        (label, formatted, _), token, token_address = fields[0]
        self.assertEqual(label, "Share ticker")
        self.assertEqual(formatted, "kmgcEURC")
        self.assertIsNone(token)
        self.assertIsNone(token_address)

    # --- path byte-slices (`token.[-20:]` etc.) ---

    def test_from_proto_path_slice(self):
        # The optional terminal slice decodes into a trailing step tuple.
        def decoded(**kwargs):
            info = EthereumERC7730FieldInfo(
                path=EthereumERC7730Path(**kwargs),
                label="Field",
                formatter=FT.FORMATTER_RAW,
            )
            return FieldDefinition.from_proto(info).path

        self.assertEqual(decoded(path=[0]), (0,))
        # token.[-20:]
        self.assertEqual(decoded(path=[0], slice_start=-20), (0, (-20,)))
        # params.path.[0:20]
        self.assertEqual(
            decoded(path=[1, 0], slice_start=0, slice_end=20), (1, 0, (0, 20))
        )
        # takerTraits.[:1] - start defaults to 0
        self.assertEqual(decoded(path=[2], slice_end=1), (2, (0, 1)))

    def test_packed_address_slice_end_to_end(self):
        # The 1inch `Address` pattern: a uint256 whose low 20 bytes are an
        # address and whose high bits carry flags. The parameter parses as a
        # plain uint256 (faithful to the ABI); the field's `[-20:]` slice
        # views the value as its EVM word and clips the flags (_word_bytes).
        # The second parameter is the `goodUntil.[-4:]` shape: a date packed
        # into the low bytes of a bytes32.
        class _Defs:
            network = make_eth_network()

        addr_hex = "d8da6bf26964af9d7eed9e03e53415d37aa96045"
        flags = (1 << 255) | (1 << 160)
        packed_address = flags | int.from_bytes(bytes.fromhex(addr_hex), "big")

        display_format = DisplayFormat(
            binding_context=None,
            func_sig=b"\x00\x00\x00\x00",
            provider_name=None,
            intent="Test",
            parameter_definitions=[
                Atomic(parse_uint256),  # packed address
                Atomic(parse_bytes32),  # packed date
            ],
            field_definitions=[
                FieldDefinition((0, (-20,)), "Beneficiary", AddressNameFormatter),
                FieldDefinition((1, (-4,)), "Expires", DateFormatter),
            ],
        )

        calldata = to_bytes(packed_address) + to_bytes(1616051824)
        parameters, fields = await_result(
            display_format.parse_calldata(memoryview(calldata), None, _Defs())
        )

        # the parsed parameter keeps the full packed value
        self.assertEqual(parameters[0], packed_address)

        (label, formatted, _), _, _ = fields[0]
        self.assertEqual(label, "Beneficiary")
        self.assertEqual(formatted.lower(), "0x" + addr_hex)

        (label, formatted, _), _, _ = fields[1]
        self.assertEqual(label, "Expires")
        self.assertEqual(formatted, "2021-03-18 07:17:04")

    def test_slice_of_negative_int_rejected(self):
        # Byte-slicing a signed value has no defined meaning.
        display_format = DisplayFormat(
            binding_context=None,
            func_sig=b"\x00\x00\x00\x00",
            provider_name=None,
            intent="Test",
            parameter_definitions=[Atomic(parse_int160)],
            field_definitions=[FieldDefinition((0, (-20,)), "Field", RawFormatter)],
        )
        minus_one = ((1 << 256) - 1).to_bytes(32, "big")
        with self.assertRaises(InvalidFormatDefinition):
            await_result(
                display_format.parse_calldata(memoryview(minus_one), None, None)
            )

    # --- tokenAmount with a constant (literal) token address ---

    def test_from_proto_token_amount_constant_token(self):
        # Regression test for `from_proto`
        # Might use a .proto binary blob in future.
        token_addr = bytes.fromhex("ae7ab96520de3a18e5e111b5eaab095312d7fe84")  # stETH
        info = EthereumERC7730FieldInfo(
            path=EthereumERC7730Path(path=[0]),
            label="Amount",
            formatter=FT.FORMATTER_TOKEN_AMOUNT,
            const_token_address=token_addr,
        )
        fmt = FieldDefinition.from_proto(info).get_formatter()
        self.assertIsInstance(fmt, TokenAmountFormatter)
        self.assertEqual(fmt.const_token_address, token_addr)
        self.assertIsNone(fmt.token_path)

    def test_token_amount_constant_token_format(self):
        # The token is resolved from `defs` by the constant address, without
        # touching the calldata - so `path_walker` is never called (passed None).
        token_addr = bytes.fromhex("ae7ab96520de3a18e5e111b5eaab095312d7fe84")  # stETH

        class _Defs:
            network = make_eth_network()

            def get_token(self, address):
                return make_eth_token(symbol="stETH", decimals=18, address=address)

        fmt = TokenAmountFormatter(const_token_address=token_addr)
        formatted, token, addr = await_result(
            fmt.format(2 * 10**18, None, _Defs(), None)
        )
        self.assertEqual(addr, token_addr)
        self.assertEqual(token.symbol, "stETH")
        self.assertIn("stETH", formatted)
        self.assertIn("2", formatted)

    def test_token_amount_no_token_source_rejected(self):
        # Neither token_path nor const_token_address set -> cannot resolve a token.
        fmt = TokenAmountFormatter()
        with self.assertRaises(InvalidFormatDefinition):
            await_result(fmt.format(1, None, None, None))

    # --- `calldata` fields (nested invocations) ---

    TRANSFER_SIG = b"\xa9\x05\x9c\xbb"
    RECIPIENT = bytes.fromhex("d8da6bf26964af9d7eed9e03e53415d37aa96045")
    # stETH: mapped to "Lido" in KNOWN_ADDRESSES, exercising the provider /
    # callee name resolution. Will be updated once those definitions are removed.
    CALLEE = bytes.fromhex("ae7ab96520de3a18e5e111b5eaab095312d7fe84")

    @staticmethod
    def _msg(**kwargs):
        class _Msg:
            chain_id = 1
            definitions = None
            supports_definition_request = False
            value = b"\x00"
            to = "0x0000000000000000000000000000000000000000"
            address_n = []

        msg = _Msg()
        for k, v in kwargs.items():
            setattr(msg, k, v)
        return msg

    @staticmethod
    def _defs():
        class _Defs:
            network = make_eth_network()

            def __init__(self):
                self.token_requests = []

            def get_token(self, address):
                self.token_requests.append(bytes(address))
                return make_eth_token(symbol="TST", decimals=6, address=address)

        return _Defs()

    def _transfer_blob(self):
        # ERC-20 transfer(RECIPIENT, 2 TST), selector included
        return self.TRANSFER_SIG + b"\x00" * 12 + self.RECIPIENT + to_bytes(2_000_000)

    def _outer_format(self, formatter):
        # wrapper(address callee, bytes data) with `data` displayed by `formatter`
        return DisplayFormat(
            binding_context=None,
            func_sig=b"\x00\x00\x00\x00",
            intent="Test",
            parameter_definitions=[
                Atomic(parse_address),  # callee
                DynamicLeaf(parse_bytes),  # data
            ],
            field_definitions=[FieldDefinition((1,), "Wrapped call", formatter)],
        )

    def _outer_calldata(self, blob, callee=None):
        return (
            b"\x00" * 12
            + (callee or self.CALLEE)  # left-pad the address to a 32-byte word
            + to_bytes(64)  # pointer to `data`
            + to_bytes(len(blob))
            + blob
        )

    def _expand(self, blob, formatter=None, callee=None, **parse_kwargs):
        """Run the full nested-call pipeline and return the display rows.

        Wraps `blob` (the embedded subcall's calldata) into a
        `wrapper(callee, data)` outer transaction, parses it with the outer
        display format whose one field is a calldata `formatter` (default:
        plain `CalldataFormatter` reading the callee from parameter 0), and
        returns only that expansion's rows - i.e. exactly what the subcall
        contributes to the confirm screen."""
        display_format = self._outer_format(
            formatter or CalldataFormatter(callee_path=(0,))
        )
        _, fields = await_result(
            display_format.parse_calldata(
                memoryview(self._outer_calldata(blob, callee)),
                self._msg(),
                self._defs(),
                **parse_kwargs,
            )
        )
        return fields

    def _assert_raw_fallback(self, fields, blob, callee_str="Lido"):
        # the fallback is two rows: the callee, then the raw hex blob
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0][0][:2], ("Subcall to", callee_str))
        self.assertEqual(fields[1][0][:2], ("Wrapped call", blob.hex()))
        for _, token, token_address in fields:
            self.assertIsNone(token)
            self.assertIsNone(token_address)

    def test_from_proto_calldata_formatter(self):
        info = EthereumERC7730FieldInfo(
            path=EthereumERC7730Path(path=[1]),
            label="Wrapped call",
            formatter=FT.FORMATTER_CALLDATA,
            callee_path=EthereumERC7730Path(path=[0]),
            selector=self.TRANSFER_SIG,
        )
        fmt = FieldDefinition.from_proto(info).get_formatter()
        self.assertIsInstance(fmt, CalldataFormatter)
        self.assertEqual(fmt.callee_path, (0,))
        self.assertEqual(fmt.selector, self.TRANSFER_SIG)

        # callee_path is mandatory
        info = EthereumERC7730FieldInfo(
            path=EthereumERC7730Path(path=[1]),
            label="Wrapped call",
            formatter=FT.FORMATTER_CALLDATA,
        )
        with self.assertRaises(InvalidFormatDefinition):
            FieldDefinition.from_proto(info)

        # a selector must be exactly 4 bytes
        info = EthereumERC7730FieldInfo(
            path=EthereumERC7730Path(path=[1]),
            label="Wrapped call",
            formatter=FT.FORMATTER_CALLDATA,
            callee_path=EthereumERC7730Path(path=[0]),
            selector=b"\xa9\x05",
        )
        with self.assertRaises(InvalidFormatDefinition):
            FieldDefinition.from_proto(info)

    def test_calldata_nested_transfer(self):
        # End to end: the embedded blob is an ERC-20 transfer, resolved against
        # the built-in TRANSFER format - offline, no definition requests. The
        # inner token must resolve via the *callee* (`@.to` override), not the
        # outer transaction's `to`.
        blob = self._transfer_blob()
        display_format = self._outer_format(CalldataFormatter(callee_path=(0,)))
        defs = self._defs()

        _, fields = await_result(
            display_format.parse_calldata(
                memoryview(self._outer_calldata(blob)), self._msg(), defs
            )
        )

        self.assertEqual(len(fields), 4)
        # built-in TRANSFER has no provider_name -> KNOWN_ADDRESSES fallback
        self.assertEqual(fields[0][0][:2], ("(Subcall) Provider", "Lido"))
        self.assertEqual(fields[1][0][:2], ("(Subcall) Intent", "Send"))
        (label, formatted, _), _, _ = fields[2]
        self.assertEqual(label, "(Subcall) To")
        self.assertEqual(formatted.lower(), "0x" + self.RECIPIENT.hex())
        (label, formatted, _), token, token_address = fields[3]
        self.assertEqual(label, "(Subcall) Amount")
        self.assertEqual(formatted, "2 TST")
        self.assertEqual(token.symbol, "TST")
        self.assertEqual(token_address, self.CALLEE)
        # the token was looked up by the callee address (`@.to` override)
        self.assertEqual(defs.token_requests, [self.CALLEE])

    def test_calldata_selector_param(self):
        # An explicit selector means the blob is args-only (per ERC-7730).
        blob = self._transfer_blob()[4:]  # strip the selector
        fields = self._expand(
            blob, CalldataFormatter(callee_path=(0,), selector=self.TRANSFER_SIG)
        )

        self.assertEqual(len(fields), 4)
        self.assertEqual(fields[1][0][:2], ("(Subcall) Intent", "Send"))

    def test_calldata_scalars_descriptor(self):
        # A richer inner call: the debug-only "Trezor Test Scalars" built-in
        # (7e577e01, bound to chain 1 / 0xdd..dd) exercises the address, native
        # amount, raw, unit and date formatters through the nested path.
        test_callee = b"\xdd" * 20
        note = b"hi"
        payload = b"\x01\x02"
        blob = (
            b"\x7e\x57\x7e\x01"
            + b"\x00" * 12
            + self.RECIPIENT  # recipient
            + to_bytes(10**18)  # nativeAmount: 1 FAKE
            + to_bytes(123456789)  # rawInt
            + to_bytes(12345)  # unitValue: 123.45 UNIT
            + to_bytes(1616051824)  # timestamp
            + b"\xab" * 32  # hashBytes32
            + to_bytes(1)  # flagBool
            + to_bytes(42)  # sizedUint
            + to_bytes(320)  # pointer to note
            + to_bytes(384)  # pointer to payload
            + to_bytes(len(note))
            + note
            + b"\x00" * (32 - len(note))
            + to_bytes(len(payload))
            + payload
        )

        fields = self._expand(blob, callee=test_callee)

        expected = [
            ("(Subcall) Provider", "Trezor Test. DO NOT USE"),
            ("(Subcall) Intent", "Trezor Test Scalars. DO NOT USE"),
            ("(Subcall) Recipient", None),  # checksummed, checked below
            ("(Subcall) Native Amount", "1 FAKE"),
            ("(Subcall) Raw Integer", "123456789"),
            ("(Subcall) Unit Value", "123.45 UNIT"),
            ("(Subcall) Date", "2021-03-18 07:17:04"),
            ("(Subcall) Raw Bytes32", "ab" * 32),
            ("(Subcall) Raw Bool", "True"),
            ("(Subcall) Raw Uint160", "42"),
            ("(Subcall) Raw String", "hi"),
            ("(Subcall) Raw Bytes", "0102"),
        ]
        self.assertEqual(len(fields), len(expected))
        for (label, value), ((got_label, got_value, _), _, _) in zip(expected, fields):
            self.assertEqual(got_label, label)
            if value is not None:
                self.assertEqual(got_value, value)
        recipient_value = fields[2][0][1]
        self.assertEqual(recipient_value.lower(), "0x" + self.RECIPIENT.hex())

    def test_calldata_no_inner_format_raw_fallback(self):
        # No built-in matches and definition requests are unsupported -> the
        # "easy case": the callee row plus the raw hex of the whole blob.
        blob = b"\xde\xad\xbe\xef" + to_bytes(5)
        fields = self._expand(blob)
        self._assert_raw_fallback(fields, blob)

    def test_calldata_short_blob_raw_fallback(self):
        # A blob too short to carry a selector cannot be looked up.
        blob = b"\xa9\x05"
        fields = self._expand(blob)
        self._assert_raw_fallback(fields, blob)

    def test_calldata_depth_capped_at_one(self):
        # Two levels end to end: the outer call embeds a call to a "middle"
        # format that itself contains a calldata field. The innermost blob is
        # a transfer that a lookup *would* resolve (TRANSFER is available),
        # but the depth cap renders it as callee + raw hex instead.
        from apps.ethereum.clear_signing_definitions import TRANSFER_DISPLAY_FORMAT

        innermost_callee = b"\x99" * 20  # not in KNOWN_ADDRESSES
        innermost_blob = self._transfer_blob()
        middle_format = DisplayFormat(
            binding_context=None,
            func_sig=b"\x12\x34\x56\x78",
            intent="Middle",
            parameter_definitions=[
                Atomic(parse_address),  # callee
                DynamicLeaf(parse_bytes),  # data
            ],
            field_definitions=[
                FieldDefinition((1,), "Inner call", CalldataFormatter(callee_path=(0,)))
            ],
        )
        middle_blob = b"\x12\x34\x56\x78" + self._outer_calldata(
            innermost_blob, callee=innermost_callee
        )

        original = clear_signing_definitions.all_display_formats
        clear_signing_definitions.all_display_formats = lambda: iter(
            [middle_format, TRANSFER_DISPLAY_FORMAT]
        )
        try:
            fields = self._expand(middle_blob)
        finally:
            clear_signing_definitions.all_display_formats = original

        self.assertEqual(len(fields), 4)
        self.assertEqual(fields[0][0][:2], ("(Subcall) Provider", "Lido"))
        self.assertEqual(fields[1][0][:2], ("(Subcall) Intent", "Middle"))
        # the middle format's calldata field degraded to callee + raw hex
        (label, formatted, _), _, _ = fields[2]
        self.assertEqual(label, "(Subcall) Subcall to")
        self.assertEqual(formatted.lower(), "0x" + innermost_callee.hex())
        self.assertEqual(
            fields[3][0][:2],
            ("(Subcall) Inner call", innermost_blob.hex()),
        )
        # the transfer was never resolved: no third-level formatting happened
        self.assertFalse(any("Send" == f[0][1] for f in fields))

    def test_calldata_invalid_values_rejected(self):
        msg, defs = self._msg(), self._defs()
        blob = self._transfer_blob()

        cases = [
            # field path does not resolve to bytes blob(s)
            {(0,): 5, (1,): self.CALLEE},
            {(0,): [blob, 5], (1,): self.CALLEE},  # non-bytes array element
            # callee is not a 20-byte address
            {(0,): blob, (1,): 5},
            {(0,): blob, (1,): b"\x00\x01"},
            # a callee array must match the subcall array's length
            {(0,): [blob, blob], (1,): [self.CALLEE]},
            # a single blob takes a single callee, not an array
            {(0,): blob, (1,): [self.CALLEE]},
        ]
        for values in cases:
            fmt = CalldataFormatter(callee_path=(1,))
            fd = FieldDefinition((0,), "Wrapped call", fmt)
            with self.assertRaises(InvalidFormatDefinition):
                await_result(
                    _expand_calldata_field(
                        fd, fmt, lambda path: values[path], msg, defs, False
                    )
                )

    def test_calldata_container_paths_in_nested_parse(self):
        # `@.to` resolves to the override; `@.from` and `@.value` are
        # unresolvable in a subcall.
        def format_for(path):
            return DisplayFormat(
                binding_context=None,
                func_sig=b"\x00\x00\x00\x00",
                intent="Test",
                parameter_definitions=[],
                field_definitions=[FieldDefinition(path, "Field", RawFormatter)],
            )

        override = self.CALLEE
        _, fields = await_result(
            format_for(ContainerPath.To).parse_calldata(
                memoryview(b""),
                self._msg(),
                self._defs(),
                nested=True,
                override_callee=override,
            )
        )
        self.assertEqual(fields[0][0][1], override.hex())

        for path in (ContainerPath.From, ContainerPath.Value):
            with self.assertRaises(InvalidFormatDefinition):
                await_result(
                    format_for(path).parse_calldata(
                        memoryview(b""), self._msg(), self._defs(), nested=True
                    )
                )

    def test_calldata_inner_failure_degrades_to_raw(self):
        # An inner display format exists but cannot be rendered (it references
        # `@.value`, unresolvable in a subcall) -> the subcall degrades to the
        # callee + raw hex rows instead of failing the outer transaction.
        blob = b"\x12\x34\x56\x78" + to_bytes(1)
        inner_format = DisplayFormat(
            binding_context=None,
            func_sig=b"\x12\x34\x56\x78",
            intent="Inner",
            parameter_definitions=[Atomic(parse_uint256)],
            field_definitions=[
                FieldDefinition(ContainerPath.Value, "Amount", RawFormatter)
            ],
        )

        original = clear_signing_definitions.all_display_formats
        clear_signing_definitions.all_display_formats = lambda: iter([inner_format])
        try:
            fields = self._expand(blob)
        finally:
            clear_signing_definitions.all_display_formats = original

        self._assert_raw_fallback(fields, blob)

    # --- arrays of subcalls (`bytes[] data`, e.g. a multicall) ---

    @staticmethod
    def _encode_bytes_array(blobs):
        # ABI body of a `bytes[]`: element count, one offset word per element
        # (relative to the start of the offsets block), then the
        # length-prefixed, right-padded elements.
        offsets = []
        tails = b""
        for blob in blobs:
            offsets.append(32 * len(blobs) + len(tails))
            tails += to_bytes(len(blob)) + blob + b"\x00" * (-len(blob) % 32)
        return to_bytes(len(blobs)) + b"".join(to_bytes(o) for o in offsets) + tails

    def _expand_array(self, blobs, callees=None):
        """Like `_expand`, but the wrapper is `wrapper(callee(s), bytes[] data)`:
        `data` carries one embedded subcall per element. `callees` switches the
        first parameter from a single shared address to a parallel `address[]`."""
        if callees is None:
            callee_param = Atomic(parse_address)
            calldata = b"\x00" * 12 + self.CALLEE + to_bytes(64)
        else:
            callee_param = Array(Atomic(parse_address))
            callees_body = to_bytes(len(callees)) + b"".join(
                b"\x00" * 12 + c for c in callees
            )
            calldata = to_bytes(64) + to_bytes(64 + len(callees_body)) + callees_body
        calldata += self._encode_bytes_array(blobs)

        display_format = DisplayFormat(
            binding_context=None,
            func_sig=b"\x00\x00\x00\x00",
            intent="Test",
            parameter_definitions=[callee_param, Array(DynamicLeaf(parse_bytes))],
            field_definitions=[
                FieldDefinition(
                    (1,), "Wrapped call", CalldataFormatter(callee_path=(0,))
                )
            ],
        )
        defs = self._defs()
        _, fields = await_result(
            display_format.parse_calldata(memoryview(calldata), self._msg(), defs)
        )
        return fields, defs

    def test_calldata_array_of_subcalls(self):
        # Two embedded transfers sharing one callee: each expands as its own
        # subcall, rows indexed "(Subcall #1)" / "(Subcall #2)", and the token
        # resolves per subcall via the shared callee.
        blob = self._transfer_blob()
        fields, defs = self._expand_array([blob, blob])

        self.assertEqual(len(fields), 8)
        for n, group in ((1, fields[:4]), (2, fields[4:])):
            prefix = f"(Subcall #{n}) "
            self.assertEqual(group[0][0][:2], (prefix + "Provider", "Lido"))
            self.assertEqual(group[1][0][:2], (prefix + "Intent", "Send"))
            (label, formatted, _), _, _ = group[2]
            self.assertEqual(label, prefix + "To")
            self.assertEqual(formatted.lower(), "0x" + self.RECIPIENT.hex())
            (label, formatted, _), token, token_address = group[3]
            self.assertEqual(label, prefix + "Amount")
            self.assertEqual(formatted, "2 TST")
            self.assertEqual(token.symbol, "TST")
            self.assertEqual(token_address, self.CALLEE)
        self.assertEqual(defs.token_requests, [self.CALLEE, self.CALLEE])

    def test_calldata_array_parallel_callees(self):
        # `callee_path` resolves to an `address[]` parallel to the subcall
        # array: each subcall is displayed against its own callee.
        other_callee = b"\x99" * 20  # not in KNOWN_ADDRESSES
        blob = self._transfer_blob()
        fields, defs = self._expand_array(
            [blob, blob], callees=[self.CALLEE, other_callee]
        )

        self.assertEqual(len(fields), 8)
        self.assertEqual(fields[0][0][:2], ("(Subcall #1) Provider", "Lido"))
        (label, provider, _), _, _ = fields[4]
        self.assertEqual(label, "(Subcall #2) Provider")
        self.assertEqual(provider.lower(), "0x" + other_callee.hex())
        # each subcall's token resolves via its own callee
        self.assertEqual(defs.token_requests, [self.CALLEE, other_callee])

    def test_calldata_array_raw_fallback(self):
        # Elements that cannot be clear-signed degrade independently, with the
        # index carried into the fallback rows' labels.
        good_blob = self._transfer_blob()
        bad_blob = b"\xde\xad\xbe\xef" + to_bytes(5)
        fields, _ = self._expand_array([bad_blob, good_blob])

        self.assertEqual(len(fields), 6)
        self.assertEqual(fields[0][0][:2], ("(Subcall #1) To", "Lido"))
        self.assertEqual(
            fields[1][0][:2],
            ("(Subcall #1) Wrapped call", bad_blob.hex()),
        )
        self.assertEqual(fields[2][0][:2], ("(Subcall #2) Provider", "Lido"))

    def test_calldata_array_empty(self):
        # An empty subcall array legitimately contributes no rows.
        fields, defs = self._expand_array([])
        self.assertEqual(fields, [])
        self.assertEqual(defs.token_requests, [])


if __name__ == "__main__":
    unittest.main()
