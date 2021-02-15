from micropython import const

from trezor import wire
from trezor.messages.PrevTx import PrevTx
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInput import TxInput

from apps.common.writers import write_bitcoin_varint

from .. import multisig, writers
from ..common import input_is_nonsegwit
from . import helpers
from .bitcoin import Bitcoin

if False:
    from typing import List, Optional, Union
    from .tx_info import OriginalTxInfo, TxInfo

_SIGHASH_FORKID = const(0x40)


class Bitcoinlike(Bitcoin):
    async def sign_nonsegwit_bip143_input(self, i_sign: int) -> None:
        txi = await helpers.request_tx_input(self.tx_req, i_sign, self.coin)

        if not input_is_nonsegwit(txi):
            raise wire.ProcessError("Transaction has changed during signing")
        public_key, signature = self.sign_bip143_input(txi)

        # if multisig, do a sanity check to ensure we are signing with a key that is included in the multisig
        if txi.multisig:
            multisig.multisig_pubkey_index(txi.multisig, public_key)

        # serialize input with correct signature
        script_sig = self.input_derive_script(txi, public_key, signature)
        self.write_tx_input(self.serialized_tx, txi, script_sig)
        self.set_serialized_signature(i_sign, signature)

    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        if self.coin.force_bip143:
            await self.sign_nonsegwit_bip143_input(i_sign)
        else:
            await super().sign_nonsegwit_input(i_sign)

    async def get_tx_digest(
        self,
        i: int,
        txi: TxInput,
        tx_info: Union[TxInfo, OriginalTxInfo],
        public_keys: List[bytes],
        threshold: int,
        script_pubkey: bytes,
        tx_hash: Optional[bytes] = None,
    ) -> bytes:
        if self.coin.force_bip143:
            return tx_info.hash143.preimage_hash(
                txi,
                public_keys,
                threshold,
                tx_info.tx,
                self.coin,
                self.get_sighash_type(txi),
            )
        else:
            return await super().get_tx_digest(
                i, txi, tx_info, public_keys, threshold, script_pubkey
            )

    def get_sighash_type(self, txi: TxInput) -> int:
        hashtype = super().get_sighash_type(txi)
        if self.coin.fork_id is not None:
            hashtype |= (self.coin.fork_id << 8) | _SIGHASH_FORKID
        return hashtype

    def write_tx_header(
        self,
        w: writers.Writer,
        tx: Union[SignTx, PrevTx],
        witness_marker: bool,
    ) -> None:
        writers.write_uint32(w, tx.version)  # nVersion
        if self.coin.timestamp:
            assert tx.timestamp is not None  # checked in sanitize_*
            writers.write_uint32(w, tx.timestamp)
        if witness_marker:
            write_bitcoin_varint(w, 0x00)  # segwit witness marker
            write_bitcoin_varint(w, 0x01)  # segwit witness flag

    async def write_prev_tx_footer(
        self, w: writers.Writer, tx: PrevTx, prev_hash: bytes
    ) -> None:
        await super().write_prev_tx_footer(w, tx, prev_hash)

        if self.coin.extra_data:
            offset = 0
            while offset < tx.extra_data_len:
                size = min(1024, tx.extra_data_len - offset)
                data = await helpers.request_tx_extra_data(
                    self.tx_req, offset, size, prev_hash
                )
                writers.write_bytes_unchecked(w, data)
                offset += len(data)
