import ustruct as struct
from micropython import const
from typing import TYPE_CHECKING

from trezor import wire
from trezor.crypto.hashlib import blake2b
from trezor.messages import PrevTx, SignTx, TxInput, TxOutput
from trezor.utils import HashWriter, ensure

from apps.common.coininfo import CoinInfo
from apps.common.keychain import Keychain
from apps.common.writers import write_compact_size

from ..scripts import write_bip143_script_code_prefixed
from ..writers import (
    TX_HASH_SIZE,
    get_tx_hash,
    write_bytes_fixed,
    write_bytes_reversed,
    write_tx_output,
    write_uint32,
    write_uint64,
)
from . import approvers, helpers
from .bitcoinlike import Bitcoinlike

if TYPE_CHECKING:
    from typing import Sequence
    from apps.common import coininfo
    from .sig_hasher import SigHasher
    from .tx_info import OriginalTxInfo, TxInfo
    from ..common import SigHashType
    from ..writers import Writer

OVERWINTERED = const(0x8000_0000)

class Zcashlike(Bitcoinlike):
    def __init__(
        self,
        tx: SignTx,
        keychain: Keychain,
        coin: CoinInfo,
        approver: approvers.Approver | None,
    ) -> None:
        ensure(coin.overwintered)
        super().__init__(tx, keychain, coin, approver)

        if tx.version != 4:
            raise wire.DataError("Unsupported transaction version.")

    def create_sig_hasher(self) -> SigHasher:
        return ZcashSigHasher() # TODO

    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        await self.sign_nonsegwit_bip143_input(i_sign)

    async def get_tx_digest(
        self,
        i: int,
        txi: TxInput,
        tx_info: TxInfo | OriginalTxInfo,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        script_pubkey: bytes,
        tx_hash: bytes | None = None,
    ) -> bytes:
        raise NotImplementedError

    def write_tx_header(
        self, w: Writer, tx: SignTx | PrevTx, witness_marker: bool
    ) -> None:
        pass # made by signer

    def write_tx_footer(self, w: Writer, tx: SignTx | PrevTx) -> None:
        pass
