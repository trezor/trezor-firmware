# flake8: noqa: F403,F405
from common import *  # isort:skip

import unittest

if not utils.BITCOIN_ONLY:

    from ethereum_common import *

    from apps.ethereum.clear_signing import (
        Array,
        Atomic,
        DirtyAddress,
        OutOfBounds,
        Struct,
        ValueOverflow,
        parse_address,
        parse_bool,
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
        parsed, consumed = atomic_addr.parse(data, 0)

        assert parsed == addr_bytes
        assert consumed == 32

    def test_address_parsing_invalid_padding(self):
        addr_hex = "d8da6bf26964af9d7eed9e03e53415d37aa96045"
        addr_bytes = unhexlify(addr_hex)

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
        static_struct = Struct(
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

        parsed, consumed = static_struct.parse(data, len(FIVE_RANDOM_BYTES))

        self.assertEqual(parsed, (addr_bytes, u160_val, True))
        self.assertEqual(consumed, 96)

    def test_static_struct_uint160_overflow(self):
        static_struct = Struct(
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
            static_struct.parse(data, len(FIVE_RANDOM_BYTES))

    def test_dynamic_struct_valid(self):
        dynamic_struct = Struct((parse_address, parse_string), is_dynamic=True)

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

        parsed, consumed = dynamic_struct.parse(data, len(SEVEN_RANDOM_BYTES))

        self.assertEqual(parsed, (addr, text))
        self.assertEqual(consumed, 32)  # only the initial pointer is consumed

    def test_dynamic_struct_out_of_bounds(self):
        dynamic_struct = Struct((parse_uint256,), is_dynamic=True)

        # pointer says struct starts at byte 1000, but data is only 32 bytes long
        payload = to_bytes(1000)
        data = memoryview(payload)

        with self.assertRaises(OutOfBounds):
            dynamic_struct.parse(data, 0)

    def test_array_of_addresses_valid(self):
        address_array_parser = Array(Atomic(parse_address))

        addr1 = unhexlify("d8da6bf26964af9d7eed9e03e53415d37aa96045")
        addr1_bytes = b"\x00" * (32 - 20) + addr1
        addr2 = unhexlify("71c7656ec7ab88b098defb751b7401b5f6d8976f")
        addr2_bytes = b"\x00" * (32 - 20) + addr2

        array_length = len([addr1, addr2])

        array_pointer = len(FIVE_RANDOM_BYTES) + 32  # payload start + pointer size
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
            address_array_parser.parse(data, 0)

    def test_array_of_dynamic_structs(self):
        array_parser = Array(
            Struct(
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

        parsed, consumed = array_parser.parse(data, 0)

        self.assertEqual(parsed, [(addr1, text1), (addr2, text2)])
        self.assertEqual(consumed, 32)


if __name__ == "__main__":
    unittest.main()
