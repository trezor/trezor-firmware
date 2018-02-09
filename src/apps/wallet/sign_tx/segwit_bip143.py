from trezor.crypto.hashlib import sha256
from trezor.messages.SignTx import SignTx
from trezor.messages import InputScriptType, FailureType

from apps.wallet.sign_tx.writers import *
from apps.wallet.sign_tx.scripts import output_script_p2pkh
from apps.common.hash_writer import HashWriter


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
        return get_tx_hash(self.h_prevouts, True)

    def get_sequence_hash(self) -> bytes:
        return get_tx_hash(self.h_sequence, True)

    def get_outputs_hash(self) -> bytes:
        return get_tx_hash(self.h_outputs, True)

    def preimage_hash(self, tx: SignTx, txi: TxInputType, pubkeyhash: bytes, sighash: int) -> bytes:
        h_preimage = HashWriter(sha256)

        write_uint32(h_preimage, tx.version)  # nVersion
        write_bytes(h_preimage, bytearray(self.get_prevouts_hash()))  # hashPrevouts
        write_bytes(h_preimage, bytearray(self.get_sequence_hash()))  # hashSequence
        write_bytes_rev(h_preimage, txi.prev_hash)  # outpoint
        write_uint32(h_preimage, txi.prev_index)  # outpoint

        script_code = self.derive_script_code(txi, pubkeyhash)
        write_varint(h_preimage, len(script_code))  # scriptCode length
        write_bytes(h_preimage, script_code)  # scriptCode

        write_uint64(h_preimage, txi.amount)  # amount
        write_uint32(h_preimage, txi.sequence)  # nSequence

        write_bytes(h_preimage, bytearray(self.get_outputs_hash()))  # hashOutputs
        write_uint32(h_preimage, tx.lock_time)  # nLockTime
        write_uint32(h_preimage, sighash)  # nHashType

        return get_tx_hash(h_preimage, True)

    # see https://github.com/bitcoin/bips/blob/master/bip-0143.mediawiki#specification
    # item 5 for details
    def derive_script_code(self, txi: TxInputType, pubkeyhash: bytes) -> bytearray:
        # p2wsh multisig to be implemented
        if txi.multisig:
            raise Bip143Error(FailureType.DataError, 'Bip143 multisig support to be implemented')

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
