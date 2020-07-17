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
from apps.common.keychain import Keychain
from apps.common.writers import write_bitcoin_varint

from ..common import ecdsa_hash_pubkey
from ..scripts import output_script_multisig, output_script_p2pkh
from ..writers import (
    TX_HASH_SIZE,
    get_tx_hash,
    write_bytes_fixed,
    write_bytes_prefixed,
    write_bytes_reversed,
    write_uint32,
    write_uint64,
)
from . import approvers, helpers
from .bitcoinlike import Bitcoinlike

if False:
    from typing import List, Union
    from ..writers import Writer

OVERWINTERED = const(0x80000000)


class Zcashlike(Bitcoinlike):
    def __init__(
        self,
        tx: SignTx,
        keychain: Keychain,
        coin: CoinInfo,
        approver: approvers.Approver,
    ) -> None:
        ensure(coin.overwintered)
        super().__init__(tx, keychain, coin, approver)

        if self.tx.version != 4:
            raise wire.DataError("Unsupported transaction version.")

    async def step7_finish(self) -> None:
        self.write_tx_footer(self.serialized_tx, self.tx)

        write_uint64(self.serialized_tx, 0)  # valueBalance
        write_bitcoin_varint(self.serialized_tx, 0)  # nShieldedSpend
        write_bitcoin_varint(self.serialized_tx, 0)  # nShieldedOutput
        write_bitcoin_varint(self.serialized_tx, 0)  # nJoinSplit

        await helpers.request_tx_finish(self.tx_req)

    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        await self.sign_nonsegwit_bip143_input(i_sign)

    async def get_tx_digest(
        self,
        i: int,
        txi: TxInputType,
        public_keys: List[bytes],
        threshold: int,
        script_pubkey: bytes,
    ) -> bytes:
        return self.hash143_preimage_hash(txi, public_keys, threshold)

    def write_tx_header(
        self, w: Writer, tx: Union[SignTx, TransactionType], witness_marker: bool
    ) -> None:
        if tx.version < 3:
            # pre-overwinter
            write_uint32(w, tx.version)
        else:
            # nVersion | fOverwintered
            write_uint32(w, tx.version | OVERWINTERED)
            write_uint32(w, tx.version_group_id)  # nVersionGroupId

    def write_tx_footer(self, w: Writer, tx: Union[SignTx, TransactionType]) -> None:
        write_uint32(w, tx.lock_time)
        if tx.version >= 3:
            write_uint32(w, tx.expiry)  # expiryHeight

    # ZIP-0143 / ZIP-0243
    # ===

    def init_hash143(self) -> None:
        self.h_prevouts = HashWriter(blake2b(outlen=32, personal=b"ZcashPrevoutHash"))
        self.h_sequence = HashWriter(blake2b(outlen=32, personal=b"ZcashSequencHash"))
        self.h_outputs = HashWriter(blake2b(outlen=32, personal=b"ZcashOutputsHash"))

    def hash143_preimage_hash(
        self, txi: TxInputType, public_keys: List[bytes], threshold: int
    ) -> bytes:
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
        write_uint32(h_preimage, self.get_sighash_type(txi))

        # 10a /13a. outpoint
        write_bytes_reversed(h_preimage, txi.prev_hash, TX_HASH_SIZE)
        write_uint32(h_preimage, txi.prev_index)

        # 10b / 13b. scriptCode
        script_code = derive_script_code(txi, public_keys, threshold, self.coin)
        write_bytes_prefixed(h_preimage, script_code)

        # 10c / 13c. value
        write_uint64(h_preimage, txi.amount)

        # 10d / 13d. nSequence
        write_uint32(h_preimage, txi.sequence)

        return get_tx_hash(h_preimage)


def derive_script_code(
    txi: TxInputType, public_keys: List[bytes], threshold: int, coin: CoinInfo
) -> bytearray:
    if len(public_keys) > 1:
        return output_script_multisig(public_keys, threshold)

    p2pkh = txi.script_type in (InputScriptType.SPENDADDRESS, InputScriptType.EXTERNAL)
    if p2pkh:
        return output_script_p2pkh(ecdsa_hash_pubkey(public_keys[0], coin))

    else:
        raise wire.DataError("Unknown input script type for zip143 script code")
