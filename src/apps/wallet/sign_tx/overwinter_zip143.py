from micropython import const

from trezor.crypto.hashlib import blake2b
from trezor.messages import FailureType, InputScriptType
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.utils import HashWriter

from apps.common.coininfo import CoinInfo
from apps.wallet.sign_tx.multisig import multisig_get_pubkeys
from apps.wallet.sign_tx.scripts import output_script_multisig, output_script_p2pkh
from apps.wallet.sign_tx.writers import (
    get_tx_hash,
    write_bytes,
    write_bytes_reversed,
    write_tx_output,
    write_uint32,
    write_uint64,
    write_varint,
)

OVERWINTERED = const(0x80000000)


class Zip143Error(ValueError):
    pass


class Zip143:
    def __init__(self):
        self.h_prevouts = HashWriter(blake2b, outlen=32, personal=b"ZcashPrevoutHash")
        self.h_sequence = HashWriter(blake2b, outlen=32, personal=b"ZcashSequencHash")
        self.h_outputs = HashWriter(blake2b, outlen=32, personal=b"ZcashOutputsHash")

    def add_prevouts(self, txi: TxInputType):
        write_bytes_reversed(self.h_prevouts, txi.prev_hash)
        write_uint32(self.h_prevouts, txi.prev_index)

    def add_sequence(self, txi: TxInputType):
        write_uint32(self.h_sequence, txi.sequence)

    def add_output(self, txo_bin: TxOutputBinType):
        write_tx_output(self.h_outputs, txo_bin)

    def get_prevouts_hash(self) -> bytes:
        return get_tx_hash(self.h_prevouts)

    def get_sequence_hash(self) -> bytes:
        return get_tx_hash(self.h_sequence)

    def get_outputs_hash(self) -> bytes:
        return get_tx_hash(self.h_outputs)

    def preimage_hash(
        self,
        coin: CoinInfo,
        tx: SignTx,
        txi: TxInputType,
        pubkeyhash: bytes,
        sighash: int,
    ) -> bytes:
        h_preimage = HashWriter(
            blake2b, outlen=32, personal=b"ZcashSigHash\x19\x1b\xa8\x5b"
        )  # BRANCH_ID = 0x5ba81b19

        assert tx.overwintered

        write_uint32(
            h_preimage, tx.version | OVERWINTERED
        )  # 1. nVersion | fOverwintered
        write_uint32(h_preimage, coin.version_group_id)  # 2. nVersionGroupId
        write_bytes(h_preimage, bytearray(self.get_prevouts_hash()))  # 3. hashPrevouts
        write_bytes(h_preimage, bytearray(self.get_sequence_hash()))  # 4. hashSequence
        write_bytes(h_preimage, bytearray(self.get_outputs_hash()))  # 5. hashOutputs
        write_bytes(h_preimage, b"\x00" * 32)  # 6. hashJoinSplits
        write_uint32(h_preimage, tx.lock_time)  # 7. nLockTime
        write_uint32(h_preimage, tx.expiry)  # 8. expiryHeight
        write_uint32(h_preimage, sighash)  # 9. nHashType

        write_bytes_reversed(h_preimage, txi.prev_hash)  # 10a. outpoint
        write_uint32(h_preimage, txi.prev_index)

        script_code = self.derive_script_code(txi, pubkeyhash)  # 10b. scriptCode
        write_varint(h_preimage, len(script_code))
        write_bytes(h_preimage, script_code)

        write_uint64(h_preimage, txi.amount)  # 10c. value

        write_uint32(h_preimage, txi.sequence)  # 10d. nSequence

        return get_tx_hash(h_preimage)

    # see https://github.com/bitcoin/bips/blob/master/bip-0143.mediawiki#specification
    # item 5 for details
    def derive_script_code(self, txi: TxInputType, pubkeyhash: bytes) -> bytearray:

        if txi.multisig:
            return output_script_multisig(
                multisig_get_pubkeys(txi.multisig), txi.multisig.m
            )

        p2pkh = txi.script_type == InputScriptType.SPENDADDRESS
        if p2pkh:
            return output_script_p2pkh(pubkeyhash)

        else:
            raise Zip143Error(
                FailureType.DataError,
                "Unknown input script type for zip143 script code",
            )
