import gc
from micropython import const

from trezor.crypto import cashaddr
from trezor.messages import FailureType, InputScriptType
from trezor.messages.SignTx import SignTx
from trezor.messages.TransactionType import TransactionType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType

from apps.wallet.sign_tx import addresses, helpers, multisig, signing, writers, zcash

if False:
    from typing import Union


class Bitcoinlike(signing.Bitcoin):
    def init_hash143(self) -> None:
        if self.coin.overwintered:
            if self.tx.version == 3:
                branch_id = self.tx.branch_id or 0x5BA81B19  # Overwinter
                self.hash143 = zcash.Zip143(branch_id)  # ZIP-0143 transaction hashing
            elif self.tx.version == 4:
                branch_id = self.tx.branch_id or 0x76B809BB  # Sapling
                self.hash143 = zcash.Zip243(branch_id)  # ZIP-0243 transaction hashing
            else:
                raise signing.SigningError(
                    FailureType.DataError,
                    "Unsupported version for overwintered transaction",
                )
        else:
            super().init_hash143()

    async def phase1_process_segwit_input(self, i: int, txi: TxInputType) -> None:
        if not self.coin.segwit:
            raise signing.SigningError(
                FailureType.DataError, "Segwit not enabled on this coin"
            )
        await super().phase1_process_segwit_input(i, txi)

    async def phase1_process_nonsegwit_input(self, i: int, txi: TxInputType) -> None:
        if self.coin.force_bip143 or self.coin.overwintered:
            await self.phase1_process_bip143_input(i, txi)
        else:
            await super().phase1_process_nonsegwit_input(i, txi)

    async def phase1_process_bip143_input(self, i: int, txi: TxInputType) -> None:
        if not txi.amount:
            raise signing.SigningError(
                FailureType.DataError, "Expected input with amount"
            )
        self.segwit[i] = False
        self.bip143_in += txi.amount
        self.total_in += txi.amount

    async def phase2_sign_nonsegwit_input(self, i_sign: int) -> None:
        if self.coin.force_bip143 or self.coin.overwintered:
            await self.phase2_sign_bip143_input(i_sign)
        else:
            await super().phase2_sign_nonsegwit_input(i_sign)

    async def phase2_sign_bip143_input(self, i_sign) -> None:
        # STAGE_REQUEST_SEGWIT_INPUT
        txi_sign = await helpers.request_tx_input(self.tx_req, i_sign, self.coin)
        self.input_check_wallet_path(txi_sign)
        self.input_check_multisig_fingerprint(txi_sign)

        is_bip143 = (
            txi_sign.script_type == InputScriptType.SPENDADDRESS
            or txi_sign.script_type == InputScriptType.SPENDMULTISIG
        )
        if not is_bip143 or txi_sign.amount > self.bip143_in:
            raise signing.SigningError(
                FailureType.ProcessError, "Transaction has changed during signing"
            )
        self.bip143_in -= txi_sign.amount

        key_sign = self.keychain.derive(txi_sign.address_n, self.coin.curve_name)
        key_sign_pub = key_sign.public_key()
        self.hash143_hash = self.hash143.preimage_hash(
            self.coin,
            self.tx,
            txi_sign,
            addresses.ecdsa_hash_pubkey(key_sign_pub, self.coin),
            self.get_hash_type(),
        )

        # if multisig, check if signing with a key that is included in multisig
        if txi_sign.multisig:
            multisig.multisig_pubkey_index(txi_sign.multisig, key_sign_pub)

        signature = signing.ecdsa_sign(key_sign, self.hash143_hash)

        # serialize input with correct signature
        gc.collect()
        txi_sign.script_sig = self.input_derive_script(
            txi_sign, key_sign_pub, signature
        )
        w_txi_sign = writers.empty_bytearray(
            5 + len(txi_sign.prev_hash) + 4 + len(txi_sign.script_sig) + 4
        )
        if i_sign == 0:  # serializing first input => prepend headers
            self.write_sign_tx_header(w_txi_sign, True in self.segwit.values())
        writers.write_tx_input(w_txi_sign, txi_sign)
        self.tx_req.serialized = TxRequestSerializedType(i_sign, signature, w_txi_sign)

    def on_negative_fee(self) -> None:
        # some coins require negative fees for reward TX
        if not self.coin.negative_fee:
            super().on_negative_fee()

    def get_raw_address(self, o: TxOutputType) -> bytes:
        if self.coin.cashaddr_prefix is not None and o.address.startswith(
            self.coin.cashaddr_prefix + ":"
        ):
            prefix, addr = o.address.split(":")
            version, data = cashaddr.decode(prefix, addr)
            if version == cashaddr.ADDRESS_TYPE_P2KH:
                version = self.coin.address_type
            elif version == cashaddr.ADDRESS_TYPE_P2SH:
                version = self.coin.address_type_p2sh
            else:
                raise signing.SigningError("Unknown cashaddr address type")
            return bytes([version]) + data
        else:
            return super().get_raw_address(o)

    def get_hash_type(self) -> int:
        SIGHASH_FORKID = const(0x40)
        hashtype = super().get_hash_type()
        if self.coin.fork_id is not None:
            hashtype |= (self.coin.fork_id << 8) | SIGHASH_FORKID
        return hashtype

    def write_sign_tx_footer(self, w: writers.Writer) -> None:
        super().write_sign_tx_footer(w)

        if self.coin.overwintered:
            if self.tx.version == 3:
                writers.write_uint32(w, self.tx.expiry)  # expiryHeight
                writers.write_varint(w, 0)  # nJoinSplit
            elif self.tx.version == 4:
                writers.write_uint32(w, self.tx.expiry)  # expiryHeight
                writers.write_uint64(w, 0)  # valueBalance
                writers.write_varint(w, 0)  # nShieldedSpend
                writers.write_varint(w, 0)  # nShieldedOutput
                writers.write_varint(w, 0)  # nJoinSplit
            else:
                raise signing.SigningError(
                    FailureType.DataError,
                    "Unsupported version for overwintered transaction",
                )

    def write_tx_header(
        self, w: writers.Writer, tx: Union[SignTx, TransactionType], has_segwit: bool
    ) -> None:
        if self.coin.overwintered:
            # nVersion | fOverwintered
            writers.write_uint32(w, tx.version | zcash.OVERWINTERED)
            writers.write_uint32(w, tx.version_group_id)  # nVersionGroupId
        else:
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
