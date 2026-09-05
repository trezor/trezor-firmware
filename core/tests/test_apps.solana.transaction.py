from typing import TYPE_CHECKING

from trezor.wire import DataError

from apps.common.writers import write_bytes_unchecked, write_uint8, write_uvarint
from common import unittest, utils

if not utils.BITCOIN_ONLY:
    from apps.solana.transaction import Transaction
    from apps.solana.types import AddressType

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any, Callable, Sequence, TypeVar

    from trezor.utils import Writer

    T = TypeVar("T")

    # Number of all signers, of read-only signers, and of read-only
    # non-signers, respectively.
    Header = tuple[int, int, int]
    # Program index, account indexes, and instruction data.
    RawInstruction = tuple[int, Sequence[int], AnyBytes]


BLOCKHASH = b"h" * 32


# Serialization of the legacy transaction format,
# as described in core/src/apps/solana/README.md.
# TODO: test versioned transactions as well


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


def write_tx(
    w: Writer,
    header: Header,
    accounts: Sequence[AnyBytes],
    instructions: Sequence[RawInstruction] = (),
    blockhash: AnyBytes = BLOCKHASH,
) -> None:
    write_tx_header(w, *header)
    write_compact_array(w, accounts, write_bytes_unchecked)
    write_bytes_unchecked(w, blockhash)
    write_compact_array(w, instructions, write_instruction)


def build_tx(
    header: Header,
    accounts: Sequence[AnyBytes],
    instructions: Sequence[RawInstruction] = (),
    blockhash: AnyBytes = BLOCKHASH,
) -> bytes:
    w = bytearray()
    write_tx(w, header, accounts, instructions, blockhash)
    return bytes(w)


SYSTEM_PROGRAM = bytes(32)  # base58 "11111111111111111111111111111111"
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
        for header, expected_types in vectors:
            transaction = Transaction(
                build_tx(header, TRANSFER_ACCOUNTS, [TRANSFER_INSTRUCTION])
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
        for header in vectors:
            with self.assertRaises(DataError):
                Transaction(build_tx(header, TRANSFER_ACCOUNTS, [TRANSFER_INSTRUCTION]))


if __name__ == "__main__":
    unittest.main()
