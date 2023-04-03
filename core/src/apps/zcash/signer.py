from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import DataError

from apps.bitcoin.sign_tx.bitcoinlike import Bitcoinlike

if TYPE_CHECKING:
    from typing import Sequence

    from trezor.messages import PrevTx, SignTx, TxInput, TxOutput
    from trezor.utils import HashWriter

    from apps.bitcoin.keychain import Keychain
    from apps.bitcoin.sign_tx.approvers import Approver
    from apps.bitcoin.sign_tx.tx_info import OriginalTxInfo, TxInfo
    from apps.bitcoin.writers import Writer
    from apps.common.coininfo import CoinInfo

    from .hasher import ZcashHasher

_OVERWINTERED = const(0x8000_0000)


class Zcash(Bitcoinlike):
    def __init__(
        self,
        tx: SignTx,
        keychain: Keychain,
        coin: CoinInfo,
        approver: Approver | None,
    ) -> None:
        from trezor.utils import ensure

        ensure(coin.overwintered)
        if tx.version != 5:
            raise DataError("Expected transaction version 5.")

        super().__init__(tx, keychain, coin, approver)

    def create_sig_hasher(self, tx: SignTx | PrevTx) -> ZcashHasher:
        from .hasher import ZcashHasher

        return ZcashHasher(tx)

    def create_hash_writer(self) -> HashWriter:
        # Replacement transactions are not supported
        # so this should never be called.
        raise NotImplementedError

    async def step3_verify_inputs(self) -> None:
        # Replacement transactions are not supported.

        # We don't check prevouts, because BIP-341 techniques
        # were adapted in ZIP-244 sighash algorithm.
        # see: https://github.com/zcash/zips/issues/574
        self.taproot_only = True  # turn on taproot behavior
        await super().step3_verify_inputs()
        self.taproot_only = False  # turn off taproot behavior

    async def step5_serialize_outputs(self) -> None:
        await super().step5_serialize_outputs()

    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        await self.sign_nonsegwit_bip143_input(i_sign)

    def sign_bip143_input(self, i: int, txi: TxInput) -> tuple[bytes, bytes]:
        from apps.bitcoin.common import ecdsa_sign

        node = self.keychain.derive(txi.address_n)
        signature_digest = self.tx_info.sig_hasher.hash_zip244(
            txi, self.input_derive_script(txi, node)
        )
        signature = ecdsa_sign(node, signature_digest)
        return node.public_key(), signature

    async def process_original_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        from trezor.wire import ProcessError

        raise ProcessError("Replacement transactions are not supported.")
        # Zcash transaction fees are very low
        # so there is no need to bump the fee.

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
        return self.tx_info.sig_hasher.hash_zip244(txi, script_pubkey)

    def write_tx_header(
        self, w: Writer, tx: SignTx | PrevTx, witness_marker: bool
    ) -> None:
        from apps.common.writers import write_uint32_le

        # defined in ZIP-225 (see https://zips.z.cash/zip-0225)
        assert tx.version_group_id is not None
        assert tx.branch_id is not None  # checked in sanitize_*
        assert tx.expiry is not None

        for num in (
            tx.version | _OVERWINTERED,  # nVersion | fOverwintered
            tx.version_group_id,  # nVersionGroupId
            tx.branch_id,  # nConsensusBranchId
            tx.lock_time,  # lock_time
            tx.expiry,  # expiryHeight
        ):
            write_uint32_le(w, num)

    def write_tx_footer(self, w: Writer, tx: SignTx | PrevTx) -> None:
        from apps.common.writers import write_compact_size

        # serialize Sapling bundle
        write_compact_size(w, 0)  # nSpendsSapling
        write_compact_size(w, 0)  # nOutputsSapling
        # serialize Orchard bundle
        write_compact_size(w, 0)  # nActionsOrchard

    def output_derive_script(self, txo: TxOutput) -> bytes:
        from trezor.enums import OutputScriptType

        from apps.bitcoin import scripts

        from .unified_addresses import Typecode, decode

        # unified addresses
        if txo.address is not None and txo.address[0] == "u":
            assert txo.script_type is OutputScriptType.PAYTOADDRESS

            receivers = decode(txo.address, self.coin)
            if Typecode.P2PKH in receivers:
                pubkeyhash = receivers[Typecode.P2PKH]
                return scripts.output_script_p2pkh(pubkeyhash)
            if Typecode.P2SH in receivers:
                scripthash = receivers[Typecode.P2SH]
                return scripts.output_script_p2sh(scripthash)
            raise DataError("Unified address does not include a transparent receiver.")

        # transparent addresses
        return super().output_derive_script(txo)
