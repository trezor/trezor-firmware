from trezor.crypto.hashlib import sha256
from trezor.messages import PrevTx, SignTx, TxInput, TxOutput
from trezor.utils import HashWriter

from apps.common import coininfo

from .. import scripts, writers
from ..common import tagged_hashwriter

if False:
    from typing import Protocol, Sequence

    class SigHasher(Protocol):
        def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
            ...

        def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
            ...

        def hash143(
            self,
            txi: TxInput,
            public_keys: Sequence[bytes | memoryview],
            threshold: int,
            tx: SignTx | PrevTx,
            coin: coininfo.CoinInfo,
            sighash_type: int,
        ) -> bytes:
            ...

        def hash341(
            self,
            i: int,
            tx: SignTx | PrevTx,
            sighash_type: int,
        ) -> bytes:
            ...


# BIP-0143 hash
class BitcoinSigHasher:
    def __init__(self) -> None:
        self.h_prevouts = HashWriter(sha256())
        self.h_amounts = HashWriter(sha256())
        self.h_scriptpubkeys = HashWriter(sha256())
        self.h_sequences = HashWriter(sha256())
        self.h_outputs = HashWriter(sha256())

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        writers.write_bytes_reversed(
            self.h_prevouts, txi.prev_hash, writers.TX_HASH_SIZE
        )
        writers.write_uint32(self.h_prevouts, txi.prev_index)
        writers.write_uint64(self.h_amounts, txi.amount)
        writers.write_bytes_prefixed(self.h_scriptpubkeys, script_pubkey)
        writers.write_uint32(self.h_sequences, txi.sequence)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        writers.write_tx_output(self.h_outputs, txo, script_pubkey)

    def hash143(
        self,
        txi: TxInput,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        tx: SignTx | PrevTx,
        coin: coininfo.CoinInfo,
        sighash_type: int,
    ) -> bytes:
        h_preimage = HashWriter(sha256())

        # nVersion
        writers.write_uint32(h_preimage, tx.version)

        # hashPrevouts
        prevouts_hash = writers.get_tx_hash(
            self.h_prevouts, double=coin.sign_hash_double
        )
        writers.write_bytes_fixed(h_preimage, prevouts_hash, writers.TX_HASH_SIZE)

        # hashSequence
        sequence_hash = writers.get_tx_hash(
            self.h_sequences, double=coin.sign_hash_double
        )
        writers.write_bytes_fixed(h_preimage, sequence_hash, writers.TX_HASH_SIZE)

        # outpoint
        writers.write_bytes_reversed(h_preimage, txi.prev_hash, writers.TX_HASH_SIZE)
        writers.write_uint32(h_preimage, txi.prev_index)

        # scriptCode
        scripts.write_bip143_script_code_prefixed(
            h_preimage, txi, public_keys, threshold, coin
        )

        # amount
        writers.write_uint64(h_preimage, txi.amount)

        # nSequence
        writers.write_uint32(h_preimage, txi.sequence)

        # hashOutputs
        outputs_hash = writers.get_tx_hash(self.h_outputs, double=coin.sign_hash_double)
        writers.write_bytes_fixed(h_preimage, outputs_hash, writers.TX_HASH_SIZE)

        # nLockTime
        writers.write_uint32(h_preimage, tx.lock_time)

        # nHashType
        writers.write_uint32(h_preimage, sighash_type)

        return writers.get_tx_hash(h_preimage, double=coin.sign_hash_double)

    def hash341(
        self,
        i: int,
        tx: SignTx | PrevTx,
        sighash_type: int,
    ) -> bytes:
        h_sigmsg = tagged_hashwriter(b"TapSighash")

        # sighash epoch 0
        writers.write_uint8(h_sigmsg, 0)

        # nHashType
        writers.write_uint8(h_sigmsg, sighash_type & 0xFF)

        # nVersion
        writers.write_uint32(h_sigmsg, tx.version)

        # nLockTime
        writers.write_uint32(h_sigmsg, tx.lock_time)

        # sha_prevouts
        writers.write_bytes_fixed(
            h_sigmsg, self.h_prevouts.get_digest(), writers.TX_HASH_SIZE
        )

        # sha_amounts
        writers.write_bytes_fixed(
            h_sigmsg, self.h_amounts.get_digest(), writers.TX_HASH_SIZE
        )

        # sha_scriptpubkeys
        writers.write_bytes_fixed(
            h_sigmsg, self.h_scriptpubkeys.get_digest(), writers.TX_HASH_SIZE
        )

        # sha_sequences
        writers.write_bytes_fixed(
            h_sigmsg, self.h_sequences.get_digest(), writers.TX_HASH_SIZE
        )

        # sha_outputs
        writers.write_bytes_fixed(
            h_sigmsg, self.h_outputs.get_digest(), writers.TX_HASH_SIZE
        )

        # spend_type 0 (no tapscript message extension, no annex)
        writers.write_uint8(h_sigmsg, 0)

        # input_index
        writers.write_uint32(h_sigmsg, i)

        return h_sigmsg.get_digest()
