from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.utils import BufferReader
from trezor.wire import DataError

from apps.common.writers import (
    write_bytes_unchecked,
    write_uint8,
    write_uint16_le,
    write_uint32_le,
    write_uint64_le,
    write_uvarint,
)
from common import unittest, utils

if not utils.BITCOIN_ONLY:
    from apps.solana.constants import SOLANA_BASE_FEE_LAMPORTS
    from apps.solana.transaction import Transaction
    from apps.solana.transaction.parse import parse_var_int
    from apps.solana.types import AddressType

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from collections.abc import Callable, Sequence
    from typing import Any, TypeVar

    from trezor.utils import Writer

    T = TypeVar("T")

    # Number of all signers, of read-only signers, and of read-only
    # non-signers, respectively.
    Header = tuple[int, int, int]
    # Program index, account indexes, and instruction data.
    RawInstruction = tuple[int, Sequence[int], AnyBytes]
    # Address lookup table (ALT): account, read-write and read-only indexes.
    Alt = tuple[AnyBytes, Sequence[int], Sequence[int]]
    # Priority fee, compute unit limit, loaded accounts data size limit, and
    # heap size of a v1 transaction, each None if not set.
    TxConfig = tuple[int | None, int | None, int | None, int | None]


BLOCKHASH = b"h" * 32

NO_CONFIG: TxConfig = (None, None, None, None)
# Mask bits and serialization of the TxConfig values, in the same order.
CONFIG_FIELDS = (
    (0b00011, write_uint64_le),
    (0b00100, write_uint32_le),
    (0b01000, write_uint32_le),
    (0b10000, write_uint32_le),
)


# Serialization of the legacy, v0, and v1 transaction formats,
# as described in core/src/apps/solana/README.md.


def write_compact_u16(w: Writer, n: int) -> None:
    """Protobuf varint limited to 16 bits. The limit is not enforced here, the
    parser is expected to reject anything larger."""
    write_uvarint(w, n)


def write_compact_array(
    w: Writer, items: Sequence[T], write_item: Callable[[Writer, T], Any]
) -> None:
    write_compact_u16(w, len(items))
    for item in items:
        write_item(w, item)


def write_compact_bytes(w: Writer, data: AnyBytes) -> None:
    write_compact_u16(w, len(data))
    write_bytes_unchecked(w, data)


def write_tx_header(
    w: Writer,
    required_signatures: int,
    readonly_signers: int,
    readonly_non_signers: int,
) -> None:
    write_uint8(w, required_signatures)
    write_uint8(w, readonly_signers)
    write_uint8(w, readonly_non_signers)


def write_instruction(w: Writer, instruction: RawInstruction) -> None:
    program_index, account_indexes, data = instruction
    write_uint8(w, program_index)
    write_compact_array(w, account_indexes, write_uint8)
    write_compact_bytes(w, data)


def write_alt(w: Writer, alt: Alt) -> None:
    account, rw_indexes, ro_indexes = alt
    write_bytes_unchecked(w, account)
    write_compact_array(w, rw_indexes, write_uint8)
    write_compact_array(w, ro_indexes, write_uint8)


def write_tx_body_legacy_v0(
    w: Writer,
    accounts: Sequence[AnyBytes],
    instructions: Sequence[RawInstruction],
    blockhash: AnyBytes,
    version: int | None,
    alts: Sequence[Alt],
) -> None:
    write_compact_array(w, accounts, write_bytes_unchecked)
    write_bytes_unchecked(w, blockhash)
    write_compact_array(w, instructions, write_instruction)
    if version is not None:
        write_compact_array(w, alts, write_alt)


def get_config_mask(config: TxConfig) -> int:
    config_mask = 0
    for (bits, _), value in zip(CONFIG_FIELDS, config):
        if value is not None:
            config_mask |= bits
    return config_mask


def write_tx_body_v1(
    w: Writer,
    accounts: Sequence[AnyBytes],
    instructions: Sequence[RawInstruction],
    blockhash: AnyBytes,
    config: TxConfig,
    config_mask: int | None,
) -> None:
    """If `config_mask` is None, it is computed from `config`."""
    if config_mask is None:
        config_mask = get_config_mask(config)
    write_uint32_le(w, config_mask)
    write_bytes_unchecked(w, blockhash)
    write_uint8(w, len(instructions))
    write_uint8(w, len(accounts))

    for account in accounts:
        write_bytes_unchecked(w, account)

    for (_, write_value), value in zip(CONFIG_FIELDS, config):
        if value is not None:
            write_value(w, value)

    for program_index, account_indexes, data in instructions:
        write_uint8(w, program_index)
        write_uint8(w, len(account_indexes))
        write_uint16_le(w, len(data))
    for _, account_indexes, data in instructions:
        write_bytes_unchecked(w, bytes(account_indexes))
        write_bytes_unchecked(w, data)


def build_tx(
    header: Header,
    accounts: Sequence[AnyBytes],
    instructions: Sequence[RawInstruction] = (),
    blockhash: AnyBytes = BLOCKHASH,
    version: int | None = None,
    alts: Sequence[Alt] = (),
    config: TxConfig = NO_CONFIG,
    config_mask: int | None = None,
) -> bytes:
    w = bytearray()
    if version is not None:
        write_uint8(w, 0x80 | version)
    write_tx_header(w, *header)
    if version == 1:
        write_tx_body_v1(w, accounts, instructions, blockhash, config, config_mask)
    else:
        write_tx_body_legacy_v0(w, accounts, instructions, blockhash, version, alts)
    return bytes(w)


SYSTEM_PROGRAM = bytes(32)  # base58 "11111111111111111111111111111111"
COMPUTE_BUDGET_PROGRAM = base58.decode("ComputeBudget111111111111111111111111111111")
SIGNER = b"s" * 32
RECIPIENT = b"r" * 32
TRANSFER_ACCOUNTS = (SIGNER, RECIPIENT, SYSTEM_PROGRAM)
# Transfer (instruction 2) 1000 lamports from the signer to the recipient.
TRANSFER_INSTRUCTION: RawInstruction = (
    2,
    (0, 1),
    (2).to_bytes(4, "little") + (1000).to_bytes(8, "little"),
)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSolanaCompactU16(unittest.TestCase):
    # Vectors from solana-sdk's short_vec test_deserialize():
    # https://github.com/anza-xyz/solana-sdk/blob/e2adabb20e084efe4e5a872bb5be71051130bcd8/short-vec/src/lib.rs#L337-L378

    def test_valid(self):
        vectors = (
            (b"\x00", 0x0000),
            (b"\x7f", 0x007F),
            (b"\x80\x01", 0x0080),
            (b"\xff\x01", 0x00FF),
            (b"\x80\x02", 0x0100),
            (b"\xff\x0f", 0x07FF),
            (b"\xff\x7f", 0x3FFF),
            (b"\x80\x80\x01", 0x4000),
            (b"\xff\xff\x03", 0xFFFF),
        )
        for encoded, expected in vectors:
            reader = BufferReader(encoded)
            self.assertEqual(parse_var_int(reader), expected)
            self.assertEqual(reader.remaining_count(), 0)

    def test_invalid(self):
        vectors = (
            # aliases
            (b"\x80\x00", ValueError),
            (b"\x80\x80\x00", ValueError),
            (b"\xff\x00", ValueError),
            (b"\xff\x80\x00", ValueError),
            (b"\x80\x81\x00", ValueError),
            (b"\xff\x81\x00", ValueError),
            (b"\x80\x82\x00", ValueError),
            (b"\xff\x8f\x00", ValueError),
            (b"\xff\xff\x00", ValueError),
            # too short
            (b"", EOFError),
            (b"\x80", EOFError),
            (b"\x80\x80", EOFError),
            # too long
            (b"\x80\x80\x80\x00", ValueError),
            # too large
            (b"\x80\x80\x04", ValueError),
            (b"\x80\x80\x06", ValueError),
        )
        for encoded, error in vectors:
            with self.assertRaises(error):
                parse_var_int(BufferReader(encoded))


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSolanaTransactionHeader(unittest.TestCase):
    def test_valid(self):
        # header, expected address types
        vectors = (
            (
                (1, 0, 1),
                (
                    AddressType.AddressSig,
                    AddressType.AddressRw,
                    AddressType.AddressReadOnly,
                ),
            ),
            (
                # Read-only signers may be all the signers but one.
                (2, 1, 1),
                (
                    AddressType.AddressSig,
                    AddressType.AddressSigReadOnly,
                    AddressType.AddressReadOnly,
                ),
            ),
        )
        for version in (None, 0, 1):
            for header, expected_types in vectors:
                transaction = Transaction(
                    build_tx(
                        header,
                        TRANSFER_ACCOUNTS,
                        [TRANSFER_INSTRUCTION],
                        version=version,
                    )
                )
                self.assertEqual(
                    [address[1] for address in transaction.addresses],
                    list(expected_types),
                )

    def test_invalid(self):
        # Headers rejected by Message::sanitize(), see:
        # https://github.com/anza-xyz/solana-sdk/blob/06b8acf9dfc505da943e25274454a95a5bdaa42a/message/src/legacy.rs#L166-L178
        vectors = (
            (1, 1, 1),  # no writable signer, i.e. no fee payer
            (1, 2, 1),  # more read-only signers than signers
            (0, 0, 1),  # no signers at all
            (2, 0, 2),  # signing and read-only non-signing areas overlap
        )
        for version in (None, 0, 1):
            for header in vectors:
                with self.assertRaises(DataError):
                    Transaction(
                        build_tx(
                            header,
                            TRANSFER_ACCOUNTS,
                            [TRANSFER_INSTRUCTION],
                            version=version,
                        )
                    )

    def test_unsupported_version(self):
        # A valid v0 transaction, so that nothing but the version is wrong.
        v0_tx = build_tx(
            (1, 0, 1), TRANSFER_ACCOUNTS, [TRANSFER_INSTRUCTION], version=0
        )
        with self.assertRaises(DataError):
            Transaction(b"\x82" + v0_tx[1:])


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSolanaTransactionInstructions(unittest.TestCase):
    def test_instruction_id(self):
        transaction = Transaction(
            build_tx((1, 0, 1), TRANSFER_ACCOUNTS, [TRANSFER_INSTRUCTION])
        )

        # The parsed instruction keeps the whole data.
        ((program_index, accounts, data),) = transaction.raw_instructions
        self.assertEqual(program_index, 2)
        self.assertEqual(accounts, [0, 1])
        self.assertEqual(bytes(data), TRANSFER_INSTRUCTION[2])

        # The instruction id is split off when the instruction is created.
        (transfer,) = transaction.instructions
        self.assertEqual(transfer.instruction_id, 2)
        self.assertEqual(bytes(transfer.instruction_data), (1000).to_bytes(8, "little"))

    def test_data_shorter_than_instruction_id(self):
        # System Program instruction ids take 4 bytes.
        short_instruction = (2, (0, 1), b"\x02\x00")
        transaction = Transaction(
            build_tx(
                (1, 0, 1),
                TRANSFER_ACCOUNTS,
                [short_instruction, TRANSFER_INSTRUCTION],
            )
        )
        short, transfer = transaction.instructions

        # The whole data is kept and the instruction is shown as unsupported.
        self.assertIsNone(short.instruction_id)
        self.assertFalse(short.is_instruction_supported)
        self.assertEqual(bytes(short.instruction_data), b"\x02\x00")
        self.assertTrue(transaction.blind_signing)

        # The following instruction is not affected.
        self.assertEqual(transfer.instruction_id, 2)
        self.assertEqual(transfer.lamports, 1000)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSolanaTransactionAlts(unittest.TestCase):
    def test_without_alts(self):
        for version in (None, 0, 1):
            transaction = Transaction(
                build_tx(
                    (1, 0, 1),
                    TRANSFER_ACCOUNTS,
                    [TRANSFER_INSTRUCTION],
                    version=version,
                )
            )
            self.assertEqual(transaction.version, version)
            self.assertEqual(transaction.address_lookup_tables_rw_addresses, [])
            self.assertEqual(transaction.address_lookup_tables_ro_addresses, [])

    def test_unexpected_alts(self):
        # Only v0 transactions end with an ALT list.
        alts = bytearray()
        write_compact_array(alts, [(b"t" * 32, (5,), (7,))], write_alt)
        for version in (None, 1):
            serialized_tx = build_tx(
                (1, 0, 1),
                TRANSFER_ACCOUNTS,
                [TRANSFER_INSTRUCTION],
                version=version,
            )
            with self.assertRaises(DataError):
                Transaction(serialized_tx + alts)

    def test_v0_with_alt(self):
        table = b"t" * 32
        # Transfer to index 2, i.e. the first address loaded from the table
        # right after the static accounts.
        transfer_instruction = (1, (0, 2), TRANSFER_INSTRUCTION[2])
        transaction = Transaction(
            build_tx(
                (1, 0, 1),
                (SIGNER, SYSTEM_PROGRAM),
                [transfer_instruction],
                version=0,
                alts=[(table, (5,), (7,))],
            )
        )
        self.assertEqual(
            transaction.address_lookup_tables_rw_addresses,
            [(table, 5, AddressType.AddressRw)],
        )
        self.assertEqual(
            transaction.address_lookup_tables_ro_addresses,
            [(table, 7, AddressType.AddressReadOnly)],
        )
        (transfer,) = transaction.instructions
        self.assertEqual(transfer.recipient_account, (table, 5, AddressType.AddressRw))

    def test_v0_missing_alts(self):
        # Unlike legacy, v0 must end with the (possibly empty) ALT list.
        legacy_tx = build_tx((1, 0, 1), TRANSFER_ACCOUNTS, [TRANSFER_INSTRUCTION])
        with self.assertRaises(EOFError):
            Transaction(b"\x80" + legacy_tx)


def raw_instructions(transaction: Transaction) -> list[tuple]:
    # Instruction data are memoryviews, which can't be compared directly.
    return [
        (program_index, accounts, bytes(data))
        for program_index, accounts, data in transaction.raw_instructions
    ]


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSolanaTransactionV1(unittest.TestCase):
    def test_known_answer(self):
        # The serialized transaction from solana-sdk's
        # byte_layout_with_config() test, prefixed with the version:
        # https://github.com/anza-xyz/solana-sdk/blob/891412dceb0a7d3d4116ac295eef519882138090/message/src/versions/v1/message.rs#L1155-L1193
        serialized_tx = (
            b"\x81"
            + bytes((1, 0, 0))  # header
            + (0b111).to_bytes(4, "little")  # config mask
            + b"\xbb" * 32  # blockhash
            + bytes((1, 2))  # number of instructions and addresses
            + b"\x01" * 32
            + b"\x02" * 32
            + (0x0102030405060708).to_bytes(8, "little")  # priority fee
            + (0x11223344).to_bytes(4, "little")  # compute unit limit
            + bytes((1, 0))
            + (0).to_bytes(2, "little")  # instruction header
        )
        transaction = Transaction(serialized_tx)

        self.assertEqual(transaction.version, 1)
        self.assertEqual(transaction.blockhash, b"\xbb" * 32)
        self.assertEqual(
            [address for address, _ in transaction.addresses],
            [b"\x01" * 32, b"\x02" * 32],
        )
        self.assertEqual(raw_instructions(transaction), [(1, [], b"")])
        fee = transaction.calculate_fee()
        assert fee is not None
        self.assertEqual(fee.priority, 0x0102030405060708)

    def test_same_as_legacy(self):
        instructions = (
            TRANSFER_INSTRUCTION,
            (2, (1, 0, 1), b"\xff" * 300),
        )
        legacy = Transaction(build_tx((1, 0, 1), TRANSFER_ACCOUNTS, instructions))
        v1 = Transaction(
            build_tx(
                (1, 0, 1),
                TRANSFER_ACCOUNTS,
                instructions,
                version=1,
                config=(12_345, 200_000, 64 * 1024, 64 * 1024),
            )
        )

        self.assertEqual(v1.version, 1)
        self.assertEqual(v1.addresses, legacy.addresses)
        self.assertEqual(v1.blockhash, legacy.blockhash)
        self.assertEqual(raw_instructions(v1), raw_instructions(legacy))

    def test_invalid_config(self):
        vectors = (
            # mask, config
            (0b10_0000, NO_CONFIG),  # unknown bit
            # Only one of the two priority fee bits set.
            (0b01, (777, None, None, None)),
            (0b10, (777, None, None, None)),
        )
        for mask, config in vectors:
            with self.assertRaises(DataError):
                Transaction(
                    build_tx(
                        (1, 0, 1),
                        TRANSFER_ACCOUNTS,
                        [TRANSFER_INSTRUCTION],
                        version=1,
                        config=config,
                        config_mask=mask,
                    )
                )

    def test_fee(self):
        header = (1, 0, 2)
        accounts = (SIGNER, RECIPIENT, SYSTEM_PROGRAM, COMPUTE_BUDGET_PROGRAM)
        instructions = (
            # Set Compute Unit Limit
            (3, (), b"\x02" + (300_000).to_bytes(4, "little")),
            # Set Compute Unit Price (microlamports)
            (3, (), b"\x03" + (2_000_000).to_bytes(8, "little")),
            TRANSFER_INSTRUCTION,
        )
        legacy_fee = Transaction(
            build_tx(header, accounts, instructions)
        ).calculate_fee()
        assert legacy_fee is not None
        self.assertEqual(legacy_fee.base, SOLANA_BASE_FEE_LAMPORTS)
        self.assertEqual(legacy_fee.priority, 600_000)  # limit * price in lamports

        # v1 ignores ComputeBudget instructions, the fee comes from the config.
        for config, priority_fee in ((NO_CONFIG, 0), ((777, None, None, None), 777)):
            fee = Transaction(
                build_tx(header, accounts, instructions, version=1, config=config)
            ).calculate_fee()
            assert fee is not None
            self.assertEqual(fee.base, SOLANA_BASE_FEE_LAMPORTS)
            self.assertEqual(fee.priority, priority_fee)


if __name__ == "__main__":
    unittest.main()
