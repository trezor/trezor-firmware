import gc
from micropython import const

from trezor.messages import FailureType
from trezor.messages.SignTx import SignTx
from trezor.messages.TransactionType import TransactionType
from trezor.messages.TxInputType import TxInputType

from apps.wallet.sign_tx import helpers, multisig, writers
from apps.wallet.sign_tx.bitcoin import Bitcoin, input_is_nonsegwit
from apps.wallet.sign_tx.common import SigningError

if False:
    from typing import Union

_SIGHASH_FORKID = const(0x40)


class Bitcoinlike(Bitcoin):
    async def process_segwit_input(self, i: int, txi: TxInputType) -> None:
        if not self.coin.segwit:
            raise SigningError(FailureType.DataError, "Segwit not enabled on this coin")
        await super().process_segwit_input(i, txi)

    async def process_nonsegwit_input(self, i: int, txi: TxInputType) -> None:
        if self.coin.force_bip143:
            await self.process_bip143_input(i, txi)
        else:
            await super().process_nonsegwit_input(i, txi)

    async def sign_nonsegwit_bip143_input(self, i_sign: int) -> None:
        txi = await helpers.request_tx_input(self.tx_req, i_sign, self.coin)

        if not input_is_nonsegwit(txi):
            raise SigningError(
                FailureType.ProcessError, "Transaction has changed during signing"
            )
        public_key, signature = self.sign_bip143_input(txi)

        # if multisig, do a sanity check to ensure we are signing with a key that is included in the multisig
        if txi.multisig:
            multisig.multisig_pubkey_index(txi.multisig, public_key)

        # serialize input with correct signature
        gc.collect()
        txi.script_sig = self.input_derive_script(txi, public_key, signature)
        writers.write_tx_input(self.serialized_tx, txi)
        self.set_serialized_signature(i_sign, signature)

    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        if self.coin.force_bip143:
            await self.sign_nonsegwit_bip143_input(i_sign)
        else:
            await super().sign_nonsegwit_input(i_sign)

    def on_negative_fee(self) -> None:
        # some coins require negative fees for reward TX
        if not self.coin.negative_fee:
            super().on_negative_fee()

    def get_hash_type(self) -> int:
        hashtype = super().get_hash_type()
        if self.coin.fork_id is not None:
            hashtype |= (self.coin.fork_id << 8) | _SIGHASH_FORKID
        return hashtype

    def write_tx_header(
        self, w: writers.Writer, tx: Union[SignTx, TransactionType], has_segwit: bool
    ) -> None:
        writers.write_uint32(w, tx.version)  # nVersion
        if self.coin.timestamp:
            writers.write_uint32(w, tx.timestamp)
        if has_segwit:
            writers.write_varint(w, 0x00)  # segwit witness marker
            writers.write_varint(w, 0x01)  # segwit witness flag

    async def write_prev_tx_footer(
        self, w: writers.Writer, tx: TransactionType, prev_hash: bytes
    ) -> None:
        await super().write_prev_tx_footer(w, tx, prev_hash)

        if self.coin.extra_data:
            ofs = 0
            while ofs < tx.extra_data_len:
                size = min(1024, tx.extra_data_len - ofs)
                data = await helpers.request_tx_extra_data(
                    self.tx_req, ofs, size, prev_hash
                )
                writers.write_bytes_unchecked(w, data)
                ofs += len(data)
