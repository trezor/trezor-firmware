"""
Implementation of Zcash txid and sighash algorithms
according to the ZIP-244.

specification: https://zips.z.cash/zip-0244
"""

from typing import TYPE_CHECKING

from trezor import utils
from trezor.crypto.hashlib import blake2b
from trezor.utils import HashWriter, empty_bytearray

from apps.bitcoin.common import SigHashType
from apps.bitcoin.writers import (
    TX_HASH_SIZE,
    write_bytes_fixed,
    write_bytes_prefixed,
    write_bytes_reversed,
    write_tx_output,
    write_uint8,
)
from apps.common.writers import write_uint32_le, write_uint64_le

if TYPE_CHECKING:
    from trezor.messages import TxInput, TxOutput, SignTx, PrevTx
    from trezor.utils import Writer
    from apps.common.coininfo import CoinInfo
    from typing import Sequence
    from enum import IntEnum
    from .orchard.crypto.builder import Action
else:
    IntEnum = object


def write_hash(w: Writer, hash: bytes) -> None:
    write_bytes_fixed(w, hash, TX_HASH_SIZE)


def write_prevout(w: Writer, txi: TxInput) -> None:
    write_bytes_reversed(w, txi.prev_hash, TX_HASH_SIZE)
    write_uint32_le(w, txi.prev_index)


def write_sint64_le(w: Writer, x: int) -> None:
    assert -0x8000_0000_0000_0000 < x <= 0x7FFF_FFFF_FFFF_FFFF
    if x < 0:
        x += 0x1_0000_0000_0000_0000  # 2**64
    write_uint64_le(w, x)


class ZcashHasher:
    def __init__(self, tx: SignTx | PrevTx):
        self.header = HeaderHasher(tx)
        self.transparent = TransparentHasher()
        self.sapling = SaplingHasher()
        self.orchard = OrchardHasher()

        assert tx.branch_id is not None  # checked in sanitize_sign_tx
        tx_hash_person = empty_bytearray(16)
        write_bytes_fixed(tx_hash_person, b"ZcashTxHash_", 12)
        write_uint32_le(tx_hash_person, tx.branch_id)
        self.tx_hash_person = bytes(tx_hash_person)

    # The `txid_digest` method is currently a dead code,
    # but we keep it for future use cases.
    def txid_digest(self) -> bytes:
        """
        Returns the transaction identifier.
        see: https://zips.z.cash/zip-0244#id4
        """
        h = HashWriter(blake2b(outlen=32, personal=self.tx_hash_person))

        write_hash(h, self.header.digest())  # T.1
        write_hash(h, self.transparent.digest())  # T.2
        write_hash(h, self.sapling.digest())  # T.3
        write_hash(h, self.orchard.digest())  # T.4

        return h.get_digest()

    def signature_digest(
        self, txi: TxInput | None = None, script_pubkey: bytes | None = None
    ) -> bytes:
        """
        Returns the transaction signature digest.
        see: https://zips.z.cash/zip-0244#id13
        """
        h = HashWriter(blake2b(outlen=32, personal=self.tx_hash_person))

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
    def __init__(self, tx: SignTx | PrevTx):
        h = HashWriter(blake2b(outlen=32, personal=b"ZTxIdHeadersHash"))

        assert tx.version_group_id is not None
        assert tx.branch_id is not None  # checked in sanitize_*
        assert tx.expiry is not None

        write_uint32_le(h, tx.version | (1 << 31))  # T.1a
        write_uint32_le(h, tx.version_group_id)  # T.1b
        write_uint32_le(h, tx.branch_id)  # T.1c
        write_uint32_le(h, tx.lock_time)  # T.1d
        write_uint32_le(h, tx.expiry)  # T.1e

        self._digest = h.get_digest()

    def digest(self) -> bytes:
        """
        Returns `T.1: header_digest` field.
        see: https://zips.z.cash/zip-0244#t-1-header-digest
        """
        return self._digest


class TransparentHasher:
    def __init__(self) -> None:
        self.prevouts = HashWriter(
            blake2b(outlen=32, personal=b"ZTxIdPrevoutHash")
        )  # a hasher for fields T.2a & S.2b

        self.amounts = HashWriter(
            blake2b(outlen=32, personal=b"ZTxTrAmountsHash")
        )  # a hasher for field S.2c

        self.scriptpubkeys = HashWriter(
            blake2b(outlen=32, personal=b"ZTxTrScriptsHash")
        )  # a hasher for field S.2d

        self.sequence = HashWriter(
            blake2b(outlen=32, personal=b"ZTxIdSequencHash")
        )  # a hasher for fields T.2b & S.2e

        self.outputs = HashWriter(
            blake2b(outlen=32, personal=b"ZTxIdOutputsHash")
        )  # a hasher for fields T.2c & S.2f

        self.has_inputs = False
        self.has_outputs = False

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        self.has_inputs = True
        write_prevout(self.prevouts, txi)
        write_uint64_le(self.amounts, txi.amount)
        write_bytes_prefixed(self.scriptpubkeys, script_pubkey)
        write_uint32_le(self.sequence, txi.sequence)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self.has_outputs = True
        write_tx_output(self.outputs, txo, script_pubkey)

    def digest(self) -> bytes:
        """
        Returns `T.2: transparent_digest` field for txid computation.
        see: https://zips.z.cash/zip-0244#t-2-transparent-digest
        """
        h = HashWriter(blake2b(outlen=32, personal=b"ZTxIdTranspaHash"))

        if self.has_inputs or self.has_outputs:
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

        if not self.has_inputs:
            assert txi is None
            assert script_pubkey is None
            return self.digest()

        h = HashWriter(blake2b(outlen=32, personal=b"ZTxIdTranspaHash"))

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

    h = HashWriter(blake2b(outlen=32, personal=b"Zcash___TxInHash"))

    if txi is not None:
        assert script_pubkey is not None

        write_prevout(h, txi)  # 2.Sg.i
        write_uint64_le(h, txi.amount)  # 2.Sg.ii
        write_bytes_prefixed(h, script_pubkey)  # 2.Sg.iii
        write_uint32_le(h, txi.sequence)  # 2.Sg.iv

    return h.get_digest()


class SaplingHasher:
    """Empty Sapling bundle hasher."""

    def digest(self) -> bytes:
        """
        Returns `T.3: sapling_digest` field.
        see: https://zips.z.cash/zip-0244#t-3-sapling-digest
        """
        return blake2b(outlen=32, personal=b"ZTxIdSaplingHash").digest()


class OrchardHasherState(IntEnum):
    EMPTY = 0
    ADDING_ACTIONS = 1
    FINALIZED = 2


class OrchardHasher:
    def __init__(self) -> None:
        self.h = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrchardHash"))
        self.ch = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrcActCHash"))
        self.mh = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrcActMHash"))
        self.nh = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrcActNHash"))
        self.state = OrchardHasherState.EMPTY

    if utils.ZCASH_SHIELDED:

        def add_action(self, action: Action) -> None:
            assert self.state in (
                OrchardHasherState.EMPTY,
                OrchardHasherState.ADDING_ACTIONS,
            )
            self.state = OrchardHasherState.ADDING_ACTIONS
            encrypted = action.encrypted_note
            write_bytes_fixed(self.ch, action.nf, 32)  # T.4a.i
            write_bytes_fixed(self.ch, action.cmx, 32)  # T.4a.ii
            write_bytes_fixed(self.ch, encrypted.epk_bytes, 32)  # T.4a.iii
            write_bytes_fixed(self.ch, encrypted.enc_ciphertext[:52], 52)  # T.4a.iv

            write_bytes_fixed(self.mh, encrypted.enc_ciphertext[52:564], 512)  # T.4b.i

            write_bytes_fixed(self.nh, action.cv, 32)  # T.4c.i
            write_bytes_fixed(self.nh, action.rk, 32)  # T.4c.ii
            write_bytes_fixed(self.nh, encrypted.enc_ciphertext[564:], 16)  # T.4c.iii
            write_bytes_fixed(self.nh, encrypted.out_ciphertext, 80)  # T.4c.iv

    def finalize(self, flags: int, value_balance: int, anchor: bytes) -> None:
        assert self.state == OrchardHasherState.ADDING_ACTIONS

        write_bytes_fixed(self.h, self.ch.get_digest(), 32)  # T.4a
        write_bytes_fixed(self.h, self.mh.get_digest(), 32)  # T.4b
        write_bytes_fixed(self.h, self.nh.get_digest(), 32)  # T.4c
        write_uint8(self.h, flags)  # T.4d
        write_sint64_le(self.h, value_balance)  # T.4e
        write_bytes_fixed(self.h, anchor, 32)  # T.4f

        self.state = OrchardHasherState.FINALIZED

    def digest(self) -> bytes:
        """
        Returns `T.4: orchard_digest` field.
        see: https://zips.z.cash/zip-0244#t-4-orchard-digest
        """
        assert self.state in (OrchardHasherState.EMPTY, OrchardHasherState.FINALIZED)
        return self.h.get_digest()
