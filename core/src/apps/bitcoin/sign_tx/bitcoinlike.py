from typing import TYPE_CHECKING

from trezor import utils

from .. import writers
from . import helpers
from .bitcoin import Bitcoin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from trezor.messages import PrevTx, SignTx, TxInput

    from .tx_info import OriginalTxInfo, TxInfo


class Bitcoinlike(Bitcoin):
    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        if self.coin.force_bip143:
            await self.sign_nonsegwit_bip143_input(i_sign)
        else:
            await super().sign_nonsegwit_input(i_sign)

    async def get_tx_digest(
        self,
        i: int,
        txi: TxInput,
        tx_info: TxInfo | OriginalTxInfo,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        script_pubkey: bytes,
    ) -> bytes:
        if self.coin.force_bip143:
            # Unreachable while the opt-in is gated to coins that do not force
            # BIP-143, but this path would otherwise sign the legacy digest and
            # stamp 0x21 on it, which fails open rather than closed. ensure()
            # rather than assert, because mpy-cross runs at -O3 for release
            # builds and MicroPython does not compile assertions at all there.
            utils.ensure(not txi.unified_sighash)
            return tx_info.sig_hasher.hash143(
                txi,
                public_keys,
                threshold,
                tx_info.tx,
                self.coin,
                self.get_hash_type(txi),
            )
        else:
            return await super().get_tx_digest(
                i, txi, tx_info, public_keys, threshold, script_pubkey
            )

    def get_hash_type(self, txi: TxInput) -> int:
        from ..common import SigHashType

        hashtype = super().get_hash_type(txi)
        if self.coin.fork_id is not None:
            hashtype |= (self.coin.fork_id << 8) | SigHashType.SIGHASH_FORKID
        return hashtype

    def write_tx_header(
        self,
        w: writers.Writer,
        tx: SignTx | PrevTx,
        witness_marker: bool,
    ) -> None:
        from apps.common.writers import write_compact_size

        writers.write_uint32(w, tx.version)  # nVersion
        if self.coin.timestamp:
            assert tx.timestamp is not None  # checked in sanitize_*
            writers.write_uint32(w, tx.timestamp)
        if witness_marker:
            write_compact_size(w, 0x00)  # segwit witness marker
            write_compact_size(w, 0x01)  # segwit witness flag

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
