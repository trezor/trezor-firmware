# It assumes largest possible signature size for all inputs. For segwit
# multisig it can be .25 bytes off due to difference between segwit
# encoding (varint) vs. non-segwit encoding (op_push) of the multisig script.
#
# Heavily inspired by:
# https://github.com/trezor/trezor-mcu/commit/e1fa7af1da79e86ccaae5f3cd2a6c4644f546f8a

from micropython import const

from trezor import wire
from trezor.enums import InputScriptType

from .. import common, ownership

if False:
    from trezor.messages import TxInput

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
# maximum size of a DER signature (3 type bytes, 3 len bytes, 33 R, 32 S, 1 sighash)
_TXSIZE_DER_SIGNATURE = const(72)
# size of a Schnorr signature (32 R, 32 S, no sighash)
_TXSIZE_SCHNORR_SIGNATURE = const(64)
# size of a multiscript without pubkey (1 M, 1 N, 1 checksig)
_TXSIZE_MULTISIGSCRIPT = const(3)
# size of a p2wpkh script (1 version, 1 push, 20 hash)
_TXSIZE_WITNESSPKHASH = const(22)
# size of a p2wsh script (1 version, 1 push, 32 hash)
_TXSIZE_WITNESSSCRIPT = const(34)


class TxWeightCalculator:
    def __init__(self) -> None:
        self.inputs_count = 0
        self.outputs_count = 0
        self.counter = 4 * (_TXSIZE_HEADER + _TXSIZE_FOOTER)
        self.segwit_inputs_count = 0

    def add_input(self, i: TxInput) -> None:
        self.inputs_count += 1

        if i.multisig:
            if i.script_type == InputScriptType.SPENDTAPROOT:
                raise wire.ProcessError("Multisig not supported for taproot")

            n = len(i.multisig.nodes) if i.multisig.nodes else len(i.multisig.pubkeys)
            multisig_script_size = _TXSIZE_MULTISIGSCRIPT + n * (1 + _TXSIZE_PUBKEY)
            if i.script_type in common.SEGWIT_INPUT_SCRIPT_TYPES:
                multisig_script_size += self.varint_size(multisig_script_size)
            else:
                multisig_script_size += self.op_push_size(multisig_script_size)

            input_script_size = (
                1  # the OP_FALSE bug in multisig
                + i.multisig.m * (1 + _TXSIZE_DER_SIGNATURE)
                + multisig_script_size
            )
        elif i.script_type == InputScriptType.SPENDTAPROOT:
            input_script_size = 1 + _TXSIZE_SCHNORR_SIGNATURE
        else:
            input_script_size = 1 + _TXSIZE_DER_SIGNATURE + 1 + _TXSIZE_PUBKEY

        self.counter += 4 * _TXSIZE_INPUT

        if i.script_type in common.NONSEGWIT_INPUT_SCRIPT_TYPES:
            input_script_size += self.varint_size(input_script_size)
            self.counter += 4 * input_script_size
        elif i.script_type in common.SEGWIT_INPUT_SCRIPT_TYPES:
            self.segwit_inputs_count += 1
            if i.script_type == InputScriptType.SPENDP2SHWITNESS:
                # add script_sig size
                if i.multisig:
                    self.counter += 4 * (2 + _TXSIZE_WITNESSSCRIPT)
                else:
                    self.counter += 4 * (2 + _TXSIZE_WITNESSPKHASH)
            else:
                self.counter += 4  # empty script_sig (1 byte)
            self.counter += 1 + input_script_size  # discounted witness
        elif i.script_type == InputScriptType.EXTERNAL:
            if i.ownership_proof:
                script_sig, witness = ownership.read_scriptsig_witness(
                    i.ownership_proof
                )
                script_sig_size = len(script_sig)
                witness_size = len(witness)
            else:
                script_sig_size = len(i.script_sig or b"")
                witness_size = len(i.witness or b"")

            if witness_size > 1:
                self.segwit_inputs_count += 1

            self.counter += 4 * (self.varint_size(script_sig_size) + script_sig_size)
            self.counter += witness_size
        else:
            raise wire.DataError("Invalid script type")

    def add_output(self, script: bytes) -> None:
        self.outputs_count += 1
        script_size = self.varint_size(len(script)) + len(script)
        self.counter += 4 * (_TXSIZE_OUTPUT + script_size)

    def get_total(self) -> int:
        total = self.counter
        total += 4 * self.varint_size(self.inputs_count)
        total += 4 * self.varint_size(self.outputs_count)
        if self.segwit_inputs_count:
            total += _TXSIZE_SEGWIT_OVERHEAD
            # add one byte of witness stack item count per non-segwit input
            total += self.inputs_count - self.segwit_inputs_count

        return total

    @staticmethod
    def varint_size(length: int) -> int:
        if length < 253:
            return 1
        if length < 0x1_0000:
            return 3
        return 5

    @staticmethod
    def op_push_size(length: int) -> int:
        if length < 0x4C:
            return 1
        if length < 0x100:
            return 2
        if length < 0x1_0000:
            return 3
        return 5
