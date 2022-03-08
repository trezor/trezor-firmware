from trezor.crypto.hashlib import blake2b
from trezor.utils import HashWriter, empty_bytearray
from apps.common import writers
from apps.bitcoin.writers import (
    write_bytes_fixed,
    write_bytes_reversed,
    write_tx_output,
    write_uint32,
    write_uint64,
    write_bytes_prefixed,
    write_uint8,
    TX_HASH_SIZE,
)
from apps.bitcoin import scripts
from apps.bitcoin.common import SigHashType

from trezor import log

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from trezor.messages import TxInput, TxOutput


def write_hash(w: Writer, hash: bytes):
    write_bytes_fixed(w, hash, TX_HASH_SIZE)


def write_prevout(w: Writer, txi: TxInput):
    write_bytes_reversed(w, txi.prev_hash, TX_HASH_SIZE)
    write_uint32(w, txi.prev_index)


def write_sint64(w: Writer, n: int):
    """Writes signed 64-bit integer"""
    assert -0x8000000000000000 <= n <= 0x7FFFFFFFFFFFFFFF
    if n >= 0:
        write_uint64(w, n)
    else:
        write_uint64(w, 0x010000000000000000 + n)


class ZcashSigHasher:
    def __init__(self):
        self.header = HeaderHasher()
        self.transparent = TransparentHasher()
        self.sapling = SaplingHasher()
        self.orchard = OrchardHasher()

        self.tx_hash_person = None
        self.initialized = False

    def initialize(self, tx):
        """Initialize ZcashHasher with a transaction data."""
        self.header.initialize(tx)

        tx_hash_person = empty_bytearray(16)
        write_bytes_fixed(tx_hash_person, b'ZcashTxHash_', 12)
        write_uint32(tx_hash_person, tx.branch_id)
        self.tx_hash_person = bytes(tx_hash_person)

        self.initialized = True

    def txid_digest(self):
        """Returns the transaction identifier."""
        assert self.initialized

        h = HashWriter(blake2b(outlen=32, personal=self.tx_hash_person))

        write_hash(h, self.header.digest())       # T.1: header_digest       (32-byte hash output)
        write_hash(h, self.transparent.digest())  # T.2: transparent_digest  (32-byte hash output)
        write_hash(h, self.sapling.digest())      # T.3: sapling_digest      (32-byte hash output)
        write_hash(h, self.orchard.digest())      # T.4: orchard_digest      (32-byte hash output)

        return h.get_digest()

    def signature_digest(self, txin_sig_digest=None):
        """Returns the transaction signature digest."""
        assert self.initialized

        h = HashWriter(blake2b(outlen=32, personal=self.tx_hash_person))

        write_hash(h, self.header.digest())                          # S.1: header_digest          (32-byte hash output)
        write_hash(h, self.transparent.sig_digest(txin_sig_digest))  # S.2: transparent_sig_digest (32-byte hash output)
        write_hash(h, self.sapling.digest())                         # S.3: sapling_digest         (32-byte hash output)
        write_hash(h, self.orchard.digest())                         # S.4: orchard_digest         (32-byte hash output)

        return h.get_digest()


class HeaderHasher:
    def __init__(self):
        self._digest = None

    def initialize(self, tx):
        h = HashWriter(blake2b(outlen=32, personal=b'ZTxIdHeadersHash'))

        write_uint32(h, tx.version | (1 << 31))  # T.1a: version             (4-byte little-endian version identifier including overwinter flag)
        write_uint32(h, tx.version_group_id)     # T.1b: version_group_id    (4-byte little-endian version group identifier)
        write_uint32(h, tx.branch_id)            # T.1c: consensus_branch_id (4-byte little-endian consensus branch id)
        write_uint32(h, tx.lock_time)            # T.1d: lock_time           (4-byte little-endian nLockTime value)
        write_uint32(h, tx.expiry)               # T.1e: expiry_height       (4-byte little-endian block height)

        self._digest = h.get_digest()

    def digest(self):
        assert self._digest is not None
        return self._digest


class TransparentHasher:
    def __init__(self):
        self.prevouts =      HashWriter(blake2b(outlen=32, personal=b'ZTxIdPrevoutHash'))
        self.amounts  =      HashWriter(blake2b(outlen=32, personal=b'ZTxTrAmountsHash'))
        self.scriptpubkeys = HashWriter(blake2b(outlen=32, personal=b'ZTxTrScriptsHash'))
        self.sequence =      HashWriter(blake2b(outlen=32, personal=b'ZTxIdSequencHash'))
        self.outputs  =      HashWriter(blake2b(outlen=32, personal=b'ZTxIdOutputsHash'))
        self.empty = True  # inputs_amount + outputs_amount == 0

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        self.empty = False
        write_prevout(self.prevouts, txi)                        # (see S.2b prevouts_sig_digest)
        write_uint64(self.amounts, txi.amount)                   # (see S.2c amounts_sig_digest) 
        write_bytes_prefixed(self.scriptpubkeys, script_pubkey)  # (see S.2d scriptpubkeys_sig_digest)
        write_uint32(self.sequence, txi.sequence)                # (see S.2e sequence_sig_digest)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self.empty = False
        write_tx_output(self.outputs, txo, script_pubkey)        # (see S.2f outputs_sig_digest)

    def digest(self):
        """Returns `T.2: transparent_digest` field for txid computation."""
        h = HashWriter(blake2b(outlen=32, personal=b'ZTxIdTranspaHash'))

        if not self.empty:
            write_hash(h, self.prevouts.get_digest())  # T.2a: prevouts_digest (32-byte hash)
            write_hash(h, self.sequence.get_digest())  # T.2b: sequence_digest (32-byte hash)
            write_hash(h, self.outputs.get_digest())   # T.2c: outputs_digest  (32-byte hash)

        return h.get_digest()

    def sig_digest(self, txin_sig_digest):
        """Returns `S.2: transparent_sig_digest` field for signature digest computation."""
        if self.empty:
            assert txin_sig_digest is None
            return self.digest()

        if txin_sig_digest is None:
            txin_sig_digest = blake2b(outlen=32, personal=b'Zcash___TxInHash').digest()

        h = HashWriter(blake2b(outlen=32, personal=b'ZTxIdTranspaHash'))

        # only SIGHASH_ALL is supported in Trezor
        write_uint8(h, SigHashType.SIGHASH_ALL)         # S.2a: hash_type                (1 byte)
        write_hash(h, self.prevouts.get_digest())       # S.2b: prevouts_sig_digest      (32-byte hash)
        write_hash(h, self.amounts.get_digest())        # S.2c: amounts_sig_digest       (32-byte hash)
        write_hash(h, self.scriptpubkeys.get_digest())  # S.2d: scriptpubkeys_sig_digest (32-byte hash)
        write_hash(h, self.sequence.get_digest())       # S.2e: sequence_sig_digest      (32-byte hash)
        write_hash(h, self.outputs.get_digest())        # S.2f: outputs_sig_digest       (32-byte hash)
        write_hash(h, txin_sig_digest)                  # S.2g: txin_sig_digest          (32-byte hash)

        return h.get_digest()


def get_txin_sig_digest(
    txi: TxInput,
    public_keys: Sequence[bytes | memoryview],
    threshold: int,
    tx: SignTx | PrevTx, # no need for tx, TODO: = None
    coin: coininfo.CoinInfo,
    sighash_type: int,
):
    """Returns `S.2g: txin_sig_digest` field for signature digest computation."""
    assert sighash_type == SigHashType.SIGHASH_ALL
    h = HashWriter(blake2b(outlen=32, personal=b'Zcash___TxInHash'))

    write_prevout(h, txi)                       # S.2g.i:   prevout      (field encoding)
    write_sint64(h, txi.amount)                 # S.2g.ii:  value        (8-byte signed little-endian)
    scripts.write_bip143_script_code_prefixed(  # S.2g.iii: scriptPubKey (field encoding)
        h, txi, public_keys, threshold, coin
    )
    write_uint32(h, txi.sequence)               # S.2g.iv:  nSequence    (4-byte unsigned little-endian)

    return h.get_digest()


class SaplingHasher:
    """Empty Sapling bundle hasher."""
    def digest(self):
        """Returns `T.3: sapling_digest` field."""
        return blake2b(outlen=32, personal=b"ZTxIdSaplingHash").digest()


EMPTY = object()
ADDING_ACTIONS = object()
FINISHED = object()


class OrchardHasher:
    """Orchard bundle hasher."""

    def __init__(self):
        self.h  = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrchardHash"))
        self.ch = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrcActCHash"))
        self.mh = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrcActMHash"))
        self.nh = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrcActNHash"))
        self.state = EMPTY

    def add_action(self, action):
        assert self.state in (EMPTY, ADDING_ACTIONS)
        self.state = ADDING_ACTIONS

        write_bytes_fixed(self.ch, action["nf"], 32)                       # T.4a.i  : nullifier            (field encoding bytes)
        write_bytes_fixed(self.ch, action["cmx"], 32)                      # T.4a.ii : cmx                  (field encoding bytes)
        write_bytes_fixed(self.ch, action["epk"], 32)                      # T.4a.iii: ephemeralKey         (field encoding bytes)
        write_bytes_fixed(self.ch, action["enc_ciphertext"][:52], 52)      # T.4a.iv : encCiphertext[..52]  (First 52 bytes of field encoding)

        write_bytes_fixed(self.mh, action["enc_ciphertext"][52:564], 512)  # T.4b.i: encCiphertext[52..564] (contents of the encrypted memo field)

        write_bytes_fixed(self.nh, action["cv"], 32)                       # T.4c.i  : cv                    (field encoding bytes)
        write_bytes_fixed(self.nh, action["rk"], 32)                       # T.4c.ii : rk                    (field encoding bytes)
        write_bytes_fixed(self.nh, action["enc_ciphertext"][564:], 16)     # T.4c.iii: encCiphertext[564..]  (post-memo suffix of field encoding)
        write_bytes_fixed(self.nh, action["out_ciphertext"], 80)           # T.4c.iv : outCiphertext         (field encoding bytes)

    def finalize(self, flags, value_balance, anchor):
        assert self.state == ADDING_ACTIONS

        write_bytes_fixed(self.h, self.ch.get_digest(), 32)  # T.4a: orchard_actions_compact_digest      (32-byte hash output)
        write_bytes_fixed(self.h, self.mh.get_digest(), 32)  # T.4b: orchard_actions_memos_digest        (32-byte hash output)
        write_bytes_fixed(self.h, self.nh.get_digest(), 32)  # T.4c: orchard_actions_noncompact_digest   (32-byte hash output)
        write_bytes_fixed(self.h, flags, 1)                  # T.4d: flagsOrchard                        (1 byte)
        write_sint64(     self.h, value_balance)             # T.4e: valueBalanceOrchard                 (64-bit signed little-endian)
        write_bytes_fixed(self.h, anchor, 32)                # T.4f: anchorOrchard                       (32 bytes)

        self.state = FINISHED

    def digest(self):
        """Returns `T.4: orchard_digest` field."""
        assert self.state in (EMPTY, FINISHED)
        return self.h.get_digest()
