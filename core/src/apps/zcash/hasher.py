"""
Implementation of Zcash txid and sighash algorithms
according to the ZIP-0244.

specification: https://zips.z.cash/zip-0244
"""

from typing import TYPE_CHECKING

from trezor.crypto.hashlib import blake2b

from apps.bitcoin.writers import (
    TX_HASH_SIZE,
    write_bytes_fixed,
    write_bytes_prefixed,
    write_bytes_reversed,
    write_tx_output,
    write_uint8,
    write_uint32,
    write_uint64,
)

if TYPE_CHECKING:
    from typing import Sequence

    from trezor.messages import PrevTx, SignTx, TxInput, TxOutput
    from trezor.utils import HashWriter, Writer

    from apps.bitcoin.common import SigHashType
    from apps.common.coininfo import CoinInfo


def write_hash(w: Writer, hash: bytes) -> None:
    write_bytes_fixed(w, hash, TX_HASH_SIZE)


def write_prevout(w: Writer, txi: TxInput) -> None:
    write_bytes_reversed(w, txi.prev_hash, TX_HASH_SIZE)
    write_uint32(w, txi.prev_index)


def blake_hash_writer_32(personal: bytes) -> HashWriter:
    from trezor.utils import HashWriter

    return HashWriter(blake2b(outlen=32, personal=personal))


class ZcashHasher:
    def __init__(self, tx: SignTx | PrevTx) -> None:
        from trezor.utils import empty_bytearray

        self.header = HeaderHasher(tx)
        self.transparent = TransparentHasher()
        self.sapling = SaplingHasher()
        self.orchard = OrchardHasher()

        assert tx.branch_id is not None  # checked in sanitize_sign_tx
        tx_hash_person = empty_bytearray(16)
        write_bytes_fixed(tx_hash_person, b"ZcashTxHash_", 12)
        write_uint32(tx_hash_person, tx.branch_id)
        self.tx_hash_person = bytes(tx_hash_person)

    # The `txid_digest` method is currently a dead code,
    # but we keep it for future use cases.
    if False:  # noqa

        def txid_digest(self) -> bytes:
            """
            Returns the transaction identifier.

            see: https://zips.z.cash/zip-0244#id4
            """
            h = blake_hash_writer_32(self.tx_hash_person)

            write_hash(h, self.header.digest())  # T.1
            write_hash(h, self.transparent.digest())  # T.2
            write_hash(h, self.sapling.digest())  # T.3
            write_hash(h, self.orchard.digest())  # T.4

    def signature_digest(
        self, txi: TxInput | None, script_pubkey: bytes | None
    ) -> bytes:
        """
        Returns the transaction signature digest.

        see: https://zips.z.cash/zip-0244#id13
        """
        h = blake_hash_writer_32(self.tx_hash_person)

        write_hash(h, self.header.digest())  # S.1
        write_hash(h, self.transparent.sig_digest(txi, script_pubkey))  # S.2
        write_hash(h, self.sapling.digest())  # S.3
        write_hash(h, self.orchard.digest())  # S.4

        return h.get_digest()

    # implement `SigHasher` interface:

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        self.transparent.add_input(txi, script_pubkey)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self.transparent.add_output(txo, script_pubkey)

    def hash143(
        self,
        txi: TxInput,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        tx: SignTx | PrevTx,
        coin: CoinInfo,
        hash_type: int,
    ) -> bytes:
        raise NotImplementedError

    def hash341(
        self,
        i: int,
        tx: SignTx | PrevTx,
        sighash_type: SigHashType,
    ) -> bytes:
        raise NotImplementedError

    def hash_zip244(
        self,
        txi: TxInput | None,
        script_pubkey: bytes | None,
    ) -> bytes:
        return self.signature_digest(txi, script_pubkey)


class HeaderHasher:
    def __init__(self, tx: SignTx | PrevTx) -> None:
        h = blake_hash_writer_32(b"ZTxIdHeadersHash")

        assert tx.version_group_id is not None
        assert tx.branch_id is not None  # checked in sanitize_*
        assert tx.expiry is not None

        write_uint32(h, tx.version | (1 << 31))  # T.1a
        write_uint32(h, tx.version_group_id)  # T.1b
        write_uint32(h, tx.branch_id)  # T.1c
        write_uint32(h, tx.lock_time)  # T.1d
        write_uint32(h, tx.expiry)  # T.1e

        self._digest = h.get_digest()

    def digest(self) -> bytes:
        """
        Returns `T.1: header_digest` field.

        see: https://zips.z.cash/zip-0244#t-1-header-digest
        """
        return self._digest


class TransparentHasher:
    def __init__(self) -> None:
        # a hasher for fields T.2a & S.2b
        self.prevouts = blake_hash_writer_32(b"ZTxIdPrevoutHash")

        # a hasher for field S.2c
        self.amounts = blake_hash_writer_32(b"ZTxTrAmountsHash")

        # a hasher for field S.2d
        self.scriptpubkeys = blake_hash_writer_32(b"ZTxTrScriptsHash")

        # a hasher for fields T.2b & S.2e
        self.sequence = blake_hash_writer_32(b"ZTxIdSequencHash")

        # a hasher for fields T.2c & S.2f
        self.outputs = blake_hash_writer_32(b"ZTxIdOutputsHash")

        self.empty = True  # inputs_amount + outputs_amount == 0

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        self.empty = False

        write_prevout(self.prevouts, txi)
        write_uint64(self.amounts, txi.amount)
        write_bytes_prefixed(self.scriptpubkeys, script_pubkey)
        write_uint32(self.sequence, txi.sequence)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self.empty = False

        write_tx_output(self.outputs, txo, script_pubkey)

    def digest(self) -> bytes:
        """
        Returns `T.2: transparent_digest` field for txid computation.

        see: https://zips.z.cash/zip-0244#t-2-transparent-digest
        """
        h = blake_hash_writer_32(b"ZTxIdTranspaHash")

        if not self.empty:
            write_hash(h, self.prevouts.get_digest())  # T.2a
            write_hash(h, self.sequence.get_digest())  # T.2b
            write_hash(h, self.outputs.get_digest())  # T.2c

        return h.get_digest()

    def sig_digest(
        self,
        txi: TxInput | None,
        script_pubkey: bytes | None,
    ) -> bytes:
        """
        Returns `S.2: transparent_sig_digest` field for signature
        digest computation.

        see: https://zips.z.cash/zip-0244#s-2-transparent-sig-digest
        """
        from apps.bitcoin.common import SigHashType

        if self.empty:
            assert txi is None
            assert script_pubkey is None
            return self.digest()

        h = blake_hash_writer_32(b"ZTxIdTranspaHash")

        # only SIGHASH_ALL is supported in Trezor
        write_uint8(h, SigHashType.SIGHASH_ALL)  # S.2a
        write_hash(h, self.prevouts.get_digest())  # S.2b
        write_hash(h, self.amounts.get_digest())  # S.2c
        write_hash(h, self.scriptpubkeys.get_digest())  # S.2d
        write_hash(h, self.sequence.get_digest())  # S.2e
        write_hash(h, self.outputs.get_digest())  # S.2f
        write_hash(h, _txin_sig_digest(txi, script_pubkey))  # S.2g

        return h.get_digest()


def _txin_sig_digest(
    txi: TxInput | None,
    script_pubkey: bytes | None,
) -> bytes:
    """
    Returns `S.2g: txin_sig_digest` field for signature digest computation.

    see: https://zips.z.cash/zip-0244#s-2g-txin-sig-digest
    """

    h = blake_hash_writer_32(b"Zcash___TxInHash")

    if txi is not None:
        assert script_pubkey is not None

        write_prevout(h, txi)  # 2.Sg.i
        write_uint64(h, txi.amount)  # 2.Sg.ii
        write_bytes_prefixed(h, script_pubkey)  # 2.Sg.iii
        write_uint32(h, txi.sequence)  # 2.Sg.iv

    return h.get_digest()


class SaplingHasher:
    """
    Empty Sapling bundle hasher.
    """

    def digest(self) -> bytes:
        """
        Returns `T.3: sapling_digest` field.

        see: https://zips.z.cash/zip-0244#t-3-sapling-digest
        """
        return blake2b(outlen=32, personal=b"ZTxIdSaplingHash").digest()


class OrchardHasher:
    """
    Empty Orchard bundle hasher.
    """

    def digest(self) -> bytes:
        """
        Returns `T.4: orchard_digest` field.

        see: https://zips.z.cash/zip-0244#t-4-orchard-digest
        """
        return blake2b(outlen=32, personal=b"ZTxIdOrchardHash").digest()
