from micropython import const

from trezor.crypto.hashlib import blake256
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.utils import HashWriter

from apps.wallet.sign_tx.writers import (
    write_tx_input_decred,
    write_tx_output,
    write_uint32,
    write_varint,
)

DECRED_SERIALIZE_FULL = const(0 << 16)
DECRED_SERIALIZE_NO_WITNESS = const(1 << 16)
DECRED_SERIALIZE_WITNESS_SIGNING = const(3 << 16)

DECRED_SIGHASHALL = const(1)


class DecredPrefixHasher:
    """
    While Decred does not have the exact same implementation as bip143/zip143,
    the semantics for using the prefix hash of transactions are close enough
    that a pseudo-bip143 class can be used to store the prefix hash during the
    check_fee stage of transaction signature to then reuse it at the sign_tx
    stage without having to request the inputs again.
    """

    def __init__(self, tx: SignTx):
        self.h_prefix = HashWriter(blake256)
        self.last_output_bytes = None
        write_uint32(self.h_prefix, tx.version | DECRED_SERIALIZE_NO_WITNESS)
        write_varint(self.h_prefix, tx.inputs_count)

    def add_prevouts(self, txi: TxInputType):
        write_tx_input_decred(self.h_prefix, txi)

    def add_sequence(self, txi: TxInputType):
        pass

    def add_output_count(self, tx: SignTx):
        write_varint(self.h_prefix, tx.outputs_count)

    def add_output(self, txo_bin: TxOutputBinType):
        write_tx_output(self.h_prefix, txo_bin)

    def set_last_output_bytes(self, w_txo_bin: bytearray):
        """
        This is required because the last serialized output obtained in
        `check_fee` will only be sent to the client in `sign_tx`
        """
        self.last_output_bytes = w_txo_bin

    def get_last_output_bytes(self):
        return self.last_output_bytes

    def add_locktime_expiry(self, tx: SignTx):
        write_uint32(self.h_prefix, tx.lock_time)
        write_uint32(self.h_prefix, tx.expiry)

    def prefix_hash(self) -> bytes:
        return self.h_prefix.get_digest()
