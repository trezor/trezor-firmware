# It assumes largest possible signature size for all inputs. For segwit
# multisig it can be .25 bytes off due to difference between segwit
# encoding (varint) vs. non-segwit encoding (op_push) of the multisig script.
#
# Heavily inspired by:
# https://github.com/trezor/trezor-mcu/commit/e1fa7af1da79e86ccaae5f3cd2a6c4644f546f8a

from micropython import const

from trezor.messages import InputScriptType
from trezor.messages.TxInputType import TxInputType

# transaction header size: 4 byte version
_TXSIZE_HEADER = const(4)
# transaction footer size: 4 byte lock time
_TXSIZE_FOOTER = const(4)
# transaction segwit overhead 2 (marker, flag)
_TXSIZE_SEGWIT_OVERHEAD = const(2)

# transaction input size (without script): 32 prevhash, 4 idx, 4 sequence
_TXSIZE_INPUT = const(40)
# transaction output size (without script): 8 amount
_TXSIZE_OUTPUT = const(8)
# size of a pubkey
_TXSIZE_PUBKEY = const(33)
# size of a DER signature (3 type bytes, 3 len bytes, 33 R, 32 S, 1 sighash
_TXSIZE_SIGNATURE = const(72)
# size of a multiscript without pubkey (1 M, 1 N, 1 checksig)
_TXSIZE_MULTISIGSCRIPT = const(3)
# size of a p2wpkh script (1 version, 1 push, 20 hash)
_TXSIZE_WITNESSPKHASH = const(22)
# size of a p2wsh script (1 version, 1 push, 32 hash)
_TXSIZE_WITNESSSCRIPT = const(34)


class TxWeightCalculator:
    def __init__(self, inputs_count: int, outputs_count: int):
        self.inputs_count = inputs_count
        self.counter = 4 * (
            _TXSIZE_HEADER
            + _TXSIZE_FOOTER
            + self.ser_length_size(inputs_count)
            + self.ser_length_size(outputs_count)
        )
        self.segwit = False

    def add_witness_header(self):
        if not self.segwit:
            self.counter += _TXSIZE_SEGWIT_OVERHEAD
            self.counter += self.ser_length_size(self.inputs_count)
            self.segwit = True

    def add_input(self, i: TxInputType):

        if i.multisig:
            multisig_script_size = _TXSIZE_MULTISIGSCRIPT + len(i.multisig.pubkeys) * (
                1 + _TXSIZE_PUBKEY
            )
            input_script_size = (
                1
                + i.multisig.m * (1 + _TXSIZE_SIGNATURE)  # the OP_FALSE bug in multisig
                + self.op_push_size(multisig_script_size)
                + multisig_script_size
            )
        else:
            input_script_size = 1 + _TXSIZE_SIGNATURE + 1 + _TXSIZE_PUBKEY

        self.counter += 4 * _TXSIZE_INPUT

        if (
            i.script_type == InputScriptType.SPENDADDRESS
            or i.script_type == InputScriptType.SPENDMULTISIG
        ):
            input_script_size += self.ser_length_size(input_script_size)
            self.counter += 4 * input_script_size

        elif (
            i.script_type == InputScriptType.SPENDWITNESS
            or i.script_type == InputScriptType.SPENDP2SHWITNESS
        ):
            self.add_witness_header()
            if i.script_type == InputScriptType.SPENDP2SHWITNESS:
                if i.multisig:
                    self.counter += 4 * (2 + _TXSIZE_WITNESSSCRIPT)
                else:
                    self.counter += 4 * (2 + _TXSIZE_WITNESSPKHASH)
            else:
                self.counter += 4  # empty
            self.counter += input_script_size  # discounted witness

    def add_output(self, script: bytes):
        size = len(script) + self.ser_length_size(len(script))
        self.counter += 4 * (_TXSIZE_OUTPUT + size)

    def get_total(self) -> int:
        return self.counter

    @staticmethod
    def ser_length_size(length: int):
        if length < 253:
            return 1
        if length < 0x10000:
            return 3
        return 5

    @staticmethod
    def op_push_size(length: int):
        if length < 0x4c:
            return 1
        if length < 0x100:
            return 2
        if length < 0x10000:
            return 3
        return 5
