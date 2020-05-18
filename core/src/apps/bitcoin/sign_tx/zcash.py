import ustruct as struct
from micropython import const

from trezor import wire
from trezor.crypto.hashlib import blake2b
from trezor.messages import InputScriptType
from trezor.messages.SignTx import SignTx
from trezor.messages.TransactionType import TransactionType
from trezor.messages.TxInputType import TxInputType
from trezor.utils import HashWriter, ensure

from apps.common.coininfo import CoinInfo
from apps.common.seed import Keychain

from ..multisig import multisig_get_pubkeys
from ..scripts import output_script_multisig, output_script_p2pkh
from ..writers import (
    TX_HASH_SIZE,
    get_tx_hash,
    write_bytes_fixed,
    write_bytes_prefixed,
    write_bytes_reversed,
    write_uint32,
    write_uint64,
    write_varint,
)
from . import helpers
from .bitcoinlike import Bitcoinlike

if False:
    from typing import Union
    from .writers import Writer

OVERWINTERED = const(0x80000000)


class Overwintered(Bitcoinlike):
    def __init__(self, tx: SignTx, keychain: Keychain, coin: CoinInfo) -> None:
        ensure(coin.overwintered)
        super().__init__(tx, keychain, coin)

        if self.tx.version == 3:
            if not self.tx.branch_id:
                self.tx.branch_id = 0x5BA81B19  # Overwinter
        elif self.tx.version == 4:
            if not self.tx.branch_id:
                self.tx.branch_id = 0x76B809BB  # Sapling
        else:
            raise wire.DataError("Unsupported version for overwintered transaction")

    async def step7_finish(self) -> None:
        self.write_tx_footer(self.serialized_tx, self.tx)

        if self.tx.version == 3:
            write_uint32(self.serialized_tx, self.tx.expiry)  # expiryHeight
            write_varint(self.serialized_tx, 0)  # nJoinSplit
        elif self.tx.version == 4:
            write_uint32(self.serialized_tx, self.tx.expiry)  # expiryHeight
            write_uint64(self.serialized_tx, 0)  # valueBalance
            write_varint(self.serialized_tx, 0)  # nShieldedSpend
            write_varint(self.serialized_tx, 0)  # nShieldedOutput
            write_varint(self.serialized_tx, 0)  # nJoinSplit
        else:
            raise wire.DataError("Unsupported version for overwintered transaction")

        await helpers.request_tx_finish(self.tx_req)

    async def process_nonsegwit_input(self, txi: TxInputType) -> None:
        await self.process_bip143_input(txi)

    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        await self.sign_nonsegwit_bip143_input(i_sign)

    def write_tx_header(
        self, w: Writer, tx: Union[SignTx, TransactionType], witness_marker: bool
    ) -> None:
        # nVersion | fOverwintered
        write_uint32(w, tx.version | OVERWINTERED)
        write_uint32(w, tx.version_group_id)  # nVersionGroupId

    # ZIP-0143 / ZIP-0243
    # ===

    def init_hash143(self) -> None:
        self.h_prevouts = HashWriter(blake2b(outlen=32, personal=b"ZcashPrevoutHash"))
        self.h_sequence = HashWriter(blake2b(outlen=32, personal=b"ZcashSequencHash"))
        self.h_outputs = HashWriter(blake2b(outlen=32, personal=b"ZcashOutputsHash"))

    def hash143_preimage_hash(self, txi: TxInputType, pubkeyhash: bytes) -> bytes:
        h_preimage = HashWriter(
            blake2b(
                outlen=32,
                personal=b"ZcashSigHash" + struct.pack("<I", self.tx.branch_id),
            )
        )

        # 1. nVersion | fOverwintered
        write_uint32(h_preimage, self.tx.version | OVERWINTERED)
        # 2. nVersionGroupId
        write_uint32(h_preimage, self.tx.version_group_id)
        # 3. hashPrevouts
        write_bytes_fixed(h_preimage, get_tx_hash(self.h_prevouts), TX_HASH_SIZE)
        # 4. hashSequence
        write_bytes_fixed(h_preimage, get_tx_hash(self.h_sequence), TX_HASH_SIZE)
        # 5. hashOutputs
        write_bytes_fixed(h_preimage, get_tx_hash(self.h_outputs), TX_HASH_SIZE)

        if self.tx.version == 3:
            # 6. hashJoinSplits
            write_bytes_fixed(h_preimage, b"\x00" * TX_HASH_SIZE, TX_HASH_SIZE)
            # 7. nLockTime
            write_uint32(h_preimage, self.tx.lock_time)
            # 8. expiryHeight
            write_uint32(h_preimage, self.tx.expiry)
            # 9. nHashType
            write_uint32(h_preimage, self.get_hash_type())
        elif self.tx.version == 4:
            zero_hash = b"\x00" * TX_HASH_SIZE
            # 6. hashJoinSplits
            write_bytes_fixed(h_preimage, zero_hash, TX_HASH_SIZE)
            # 7. hashShieldedSpends
            write_bytes_fixed(h_preimage, zero_hash, TX_HASH_SIZE)
            # 8. hashShieldedOutputs
            write_bytes_fixed(h_preimage, zero_hash, TX_HASH_SIZE)
            # 9. nLockTime
            write_uint32(h_preimage, self.tx.lock_time)
            # 10. expiryHeight
            write_uint32(h_preimage, self.tx.expiry)
            # 11. valueBalance
            write_uint64(h_preimage, 0)
            # 12. nHashType
            write_uint32(h_preimage, self.get_hash_type())
        else:
            raise wire.DataError("Unsupported version for overwintered transaction")

        # 10a /13a. outpoint
        write_bytes_reversed(h_preimage, txi.prev_hash, TX_HASH_SIZE)
        write_uint32(h_preimage, txi.prev_index)

        # 10b / 13b. scriptCode
        script_code = derive_script_code(txi, pubkeyhash)
        write_bytes_prefixed(h_preimage, script_code)

        # 10c / 13c. value
        write_uint64(h_preimage, txi.amount)

        # 10d / 13d. nSequence
        write_uint32(h_preimage, txi.sequence)

        return get_tx_hash(h_preimage)


def derive_script_code(txi: TxInputType, pubkeyhash: bytes) -> bytearray:

    if txi.multisig:
        return output_script_multisig(
            multisig_get_pubkeys(txi.multisig), txi.multisig.m
        )

    p2pkh = txi.script_type == InputScriptType.SPENDADDRESS
    if p2pkh:
        return output_script_p2pkh(pubkeyhash)

    else:
        raise wire.DataError("Unknown input script type for zip143 script code")
