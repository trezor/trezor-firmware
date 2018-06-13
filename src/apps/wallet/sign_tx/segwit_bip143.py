from trezor.crypto.hashlib import sha256
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages import InputScriptType, FailureType
from trezor.utils import HashWriter

from apps.common.coininfo import CoinInfo
from apps.wallet.sign_tx.writers import write_bytes, write_bytes_rev, write_uint32, write_uint64, write_varint, write_tx_output, get_tx_hash
from apps.wallet.sign_tx.scripts import output_script_p2pkh, output_script_multisig
from apps.wallet.sign_tx.multisig import multisig_get_pubkeys


class Bip143Error(ValueError):
    pass


class Bip143:

    def __init__(self):
        self.h_prevouts = HashWriter(sha256)
        self.h_sequence = HashWriter(sha256)
        self.h_outputs = HashWriter(sha256)

    def add_prevouts(self, txi: TxInputType):
        write_bytes_rev(self.h_prevouts, txi.prev_hash)
        write_uint32(self.h_prevouts, txi.prev_index)

    def add_sequence(self, txi: TxInputType):
        write_uint32(self.h_sequence, txi.sequence)

    def add_output(self, txo_bin: TxOutputBinType):
        write_tx_output(self.h_outputs, txo_bin)

    def get_prevouts_hash(self) -> bytes:
        return get_tx_hash(self.h_prevouts, double=True)

    def get_sequence_hash(self) -> bytes:
        return get_tx_hash(self.h_sequence, double=True)

    def get_outputs_hash(self) -> bytes:
        return get_tx_hash(self.h_outputs, double=True)

    def preimage_hash(self, coin: CoinInfo, tx: SignTx, txi: TxInputType, pubkeyhash: bytes, sighash: int) -> bytes:
        h_preimage = HashWriter(sha256)

        assert not tx.overwintered

        write_uint32(h_preimage, tx.version)                          # nVersion
        write_bytes(h_preimage, bytearray(self.get_prevouts_hash()))  # hashPrevouts
        write_bytes(h_preimage, bytearray(self.get_sequence_hash()))  # hashSequence

        write_bytes_rev(h_preimage, txi.prev_hash)                    # outpoint
        write_uint32(h_preimage, txi.prev_index)                      # outpoint

        script_code = self.derive_script_code(txi, pubkeyhash)        # scriptCode
        write_varint(h_preimage, len(script_code))
        write_bytes(h_preimage, script_code)

        write_uint64(h_preimage, txi.amount)                          # amount
        write_uint32(h_preimage, txi.sequence)                        # nSequence
        write_bytes(h_preimage, bytearray(self.get_outputs_hash()))   # hashOutputs
        write_uint32(h_preimage, tx.lock_time)                        # nLockTime
        write_uint32(h_preimage, sighash)                             # nHashType

        return get_tx_hash(h_preimage, double=True)

    # see https://github.com/bitcoin/bips/blob/master/bip-0143.mediawiki#specification
    # item 5 for details
    def derive_script_code(self, txi: TxInputType, pubkeyhash: bytes) -> bytearray:

        if txi.multisig:
            return output_script_multisig(multisig_get_pubkeys(txi.multisig), txi.multisig.m)

        p2pkh = (txi.script_type == InputScriptType.SPENDWITNESS or
                 txi.script_type == InputScriptType.SPENDP2SHWITNESS or
                 txi.script_type == InputScriptType.SPENDADDRESS)
        if p2pkh:
            # for p2wpkh in p2sh or native p2wpkh
            # the scriptCode is a classic p2pkh
            return output_script_p2pkh(pubkeyhash)

        else:
            raise Bip143Error(FailureType.DataError,
                              'Unknown input script type for bip143 script code')
