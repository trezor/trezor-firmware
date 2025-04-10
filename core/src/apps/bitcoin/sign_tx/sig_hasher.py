from typing import TYPE_CHECKING

from ..writers import (
    TX_HASH_SIZE,
    write_bytes_fixed,
    write_bytes_prefixed,
    write_bytes_reversed,
    write_tx_output,
    write_uint32,
    write_uint64,
)

if TYPE_CHECKING:
    from typing import Protocol, Sequence

    from trezor.messages import PrevTx, SignTx, TxInput, TxOutput

    from apps.common import coininfo

    from ..common import SigHashType

    class SigHasher(Protocol):
        def add_input(self, txi: TxInput, script_pubkey: bytes) -> None: ...

        def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None: ...

        def hash143(
            self,
            txi: TxInput,
            public_keys: Sequence[bytes | memoryview],
            threshold: int,
            tx: SignTx | PrevTx,
            coin: coininfo.CoinInfo,
            hash_type: int,
        ) -> bytes: ...

        def hash341(
            self,
            i: int,
            tx: SignTx | PrevTx,
            sighash_type: SigHashType,
        ) -> bytes: ...

        def hash_zip244(
            self,
            txi: TxInput | None,
            script_pubkey: bytes | None,
        ) -> bytes: ...


# BIP-0143 hash
class BitcoinSigHasher:
    def __init__(self) -> None:
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter

        self.h_prevouts = HashWriter(sha256())
        self.h_amounts = HashWriter(sha256())
        self.h_scriptpubkeys = HashWriter(sha256())
        self.h_sequences = HashWriter(sha256())
        self.h_outputs = HashWriter(sha256())

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        write_bytes_reversed(self.h_prevouts, txi.prev_hash, TX_HASH_SIZE)
        write_uint32(self.h_prevouts, txi.prev_index)
        write_uint64(self.h_amounts, txi.amount)
        write_bytes_prefixed(self.h_scriptpubkeys, script_pubkey)
        write_uint32(self.h_sequences, txi.sequence)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        write_tx_output(self.h_outputs, txo, script_pubkey)

    def hash143(
        self,
        txi: TxInput,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        tx: SignTx | PrevTx,
        coin: coininfo.CoinInfo,
        hash_type: int,
    ) -> bytes:
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter

        from .. import scripts
        from ..writers import get_tx_hash

        h_preimage = HashWriter(sha256())

        # nVersion
        write_uint32(h_preimage, tx.version)

        # hashPrevouts
        prevouts_hash = get_tx_hash(self.h_prevouts, double=coin.sign_hash_double)
        write_bytes_fixed(h_preimage, prevouts_hash, TX_HASH_SIZE)

        # hashSequence
        sequence_hash = get_tx_hash(self.h_sequences, double=coin.sign_hash_double)
        write_bytes_fixed(h_preimage, sequence_hash, TX_HASH_SIZE)

        # outpoint
        write_bytes_reversed(h_preimage, txi.prev_hash, TX_HASH_SIZE)
        write_uint32(h_preimage, txi.prev_index)

        # scriptCode
        scripts.write_bip143_script_code_prefixed(
            h_preimage, txi, public_keys, threshold, coin
        )

        # amount
        write_uint64(h_preimage, txi.amount)

        # nSequence
        write_uint32(h_preimage, txi.sequence)

        # hashOutputs
        outputs_hash = get_tx_hash(self.h_outputs, double=coin.sign_hash_double)
        write_bytes_fixed(h_preimage, outputs_hash, TX_HASH_SIZE)

        # nLockTime
        write_uint32(h_preimage, tx.lock_time)

        # nHashType
        write_uint32(h_preimage, hash_type)

        return get_tx_hash(h_preimage, double=coin.sign_hash_double)

    def hash341(
        self,
        i: int,
        tx: SignTx | PrevTx,
        sighash_type: SigHashType,
    ) -> bytes:
        from ..common import tagged_hashwriter
        from ..writers import write_uint8

        h_sigmsg = tagged_hashwriter(b"TapSighash")

        # sighash epoch 0
        write_uint8(h_sigmsg, 0)

        # nHashType
        write_uint8(h_sigmsg, sighash_type & 0xFF)

        # nVersion
        write_uint32(h_sigmsg, tx.version)

        # nLockTime
        write_uint32(h_sigmsg, tx.lock_time)

        # sha_prevouts
        write_bytes_fixed(h_sigmsg, self.h_prevouts.get_digest(), TX_HASH_SIZE)

        # sha_amounts
        write_bytes_fixed(h_sigmsg, self.h_amounts.get_digest(), TX_HASH_SIZE)

        # sha_scriptpubkeys
        write_bytes_fixed(h_sigmsg, self.h_scriptpubkeys.get_digest(), TX_HASH_SIZE)

        # sha_sequences
        write_bytes_fixed(h_sigmsg, self.h_sequences.get_digest(), TX_HASH_SIZE)

        # sha_outputs
        write_bytes_fixed(h_sigmsg, self.h_outputs.get_digest(), TX_HASH_SIZE)

        # spend_type 0 (no tapscript message extension, no annex)
        write_uint8(h_sigmsg, 0)

        # input_index
        write_uint32(h_sigmsg, i)

        return h_sigmsg.get_digest()

    def hash_zip244(
        self,
        txi: TxInput | None,
        script_pubkey: bytes | None,
    ) -> bytes:
        raise NotImplementedError
