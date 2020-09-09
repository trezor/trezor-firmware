from micropython import const

from trezor import wire
from trezor.messages.SignTx import SignTx
from trezor.messages.TransactionType import TransactionType
from trezor.messages.TxInputType import TxInputType

from apps.common.writers import write_bitcoin_varint

from .. import multisig, writers
from . import helpers
from .bitcoin import Bitcoin, input_is_nonsegwit

if False:
    from typing import List, Union

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
        txi: TxInputType,
        public_keys: List[bytes],
        threshold: int,
        script_pubkey: bytes,
    ) -> bytes:
        if self.coin.force_bip143:
            return self.hash143_preimage_hash(txi, public_keys, threshold)
        else:
            return await super().get_tx_digest(
                i, txi, public_keys, threshold, script_pubkey
            )

    def get_sighash_type(self, txi: TxInputType) -> int:
        hashtype = super().get_sighash_type(txi)
        if self.coin.fork_id is not None:
            hashtype |= (self.coin.fork_id << 8) | _SIGHASH_FORKID
        return hashtype

    def write_tx_header(
        self,
        w: writers.Writer,
        tx: Union[SignTx, TransactionType],
        witness_marker: bool,
    ) -> None:
        writers.write_uint32(w, tx.version)  # nVersion
        if self.coin.timestamp:
            writers.write_uint32(w, tx.timestamp)
        if witness_marker:
            write_bitcoin_varint(w, 0x00)  # segwit witness marker
            write_bitcoin_varint(w, 0x01)  # segwit witness flag

    async def write_prev_tx_footer(
        self, w: writers.Writer, tx: TransactionType, prev_hash: bytes
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
