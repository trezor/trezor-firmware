from trezor.crypto.hashlib import blake2b
from trezor.utils import HashWriter, empty_bytearray
from apps.common import writers
from apps.bitcoin.writers import (
    write_bytes_fixed,
    write_bytes_reversed,
    write_tx_output,
    write_uint32,
    #write_uint64,
    write_uint8,
)
from apps.bitcoin import scripts

from trezor import log

if False:
    from trezor.messages import TxInput, TxOutput

SIGHASH_ALL = 1
SIGHASH_NONE = 2
SIGHASH_SINGLE = 3
SIGHASH_ANYONECANPAY = 0x80

ZCASH_ORCHARD_SIGS_HASH_PERSONALIZATION = b"ZTxAuthOrchaHash";

def write_hash(w: Writer, hash: bytes):
    write_bytes_fixed(w, hash, 32)

def write_prevout(w: Writer, txi: TxInput):
    write_bytes_reversed(w, txi.prev_hash, 32)
    write_uint32(w, txi.prev_index)

def write_sint64(w: Writer, n: int):
    assert -0x8000000000000000 <= n <= 0x7FFFFFFFFFFFFFFF
    if n >= 0:
        write_uint32(w, n)
    else:
        write_uint32(w, 0x010000000000000000 + n)

class Hasher:
    def digest(self):
        raise NotImplementedError

    def sig_digest(self):
        raise NotImplementedError

class ConstHasher(Hasher):
    def __init__(self, dig):
        self._dig = dig

    def digest(self):
        return self._dig

class Zip244TxHasher:
    def __init__(self, tx=None, header=None, transparent=None, orchard=None, sapling=None):
        # self.header = Zip244HeaderHasher(tx)
        self.transparent = Zip244TransparentHasher()
        self.sapling = Zip244SaplingHasher()
        self.orchard = Zip244OrchardHasher()
        #tx_hash_person = empty_bytearray(16)
        #write_bytes_fixed(person, b'ZcashTxHash_', 12)
        #write_uint32(tx.nConsensusBranchId)
        #self.tx_hash_person = bytes(tx_hash_person)

    def initialize(self, tx):
        self.header = Zip244HeaderHasher(tx)
        tx_hash_person = empty_bytearray(16)
        write_bytes_fixed(tx_hash_person, b'ZcashTxHash_', 12)
        write_uint32(tx_hash_person, tx.branch_id)
        self.tx_hash_person = bytes(tx_hash_person)

    def txid_digest(self):
        h = HashWriter(blake2b(outlen=32, personal=self.tx_hash_person))

        write_hash(h, self.header.digest())       # T.1: header_digest       (32-byte hash output)
        write_hash(h, self.transparent.digest())  # T.2: transparent_digest  (32-byte hash output)
        write_hash(h, self.sapling.digest())      # T.3: sapling_digest      (32-byte hash output)
        write_hash(h, self.orchard.digest())      # T.4: orchard_digest      (32-byte hash output)

        return h.get_digest()

    def signature_digest(self, *args, **kwargs):
        h = HashWriter(blake2b(outlen=32, personal=self.tx_hash_person))

        write_hash(h, self.header.digest())                          # S.1: header_digest          (32-byte hash output)
        write_hash(h, self.transparent.sig_digest(*args, **kwargs))  # S.2: transparent_sig_digest (32-byte hash output)
        write_hash(h, self.sapling.digest())                         # S.3: sapling_digest         (32-byte hash output)
        write_hash(h, self.orchard.digest())                         # S.4: orchard_digest         (32-byte hash output)

        return h.get_digest()

    # Hash143 wrappers

    def add_input(self, *args, **kwargs):
        self.transparent.add_input(*args, **kwargs)

    def add_output(self, *args, **kwargs):
        self.transparent.add_output(*args, **kwargs)
    """
    def preimage_hash(
        self,
        txi: TxInput,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        tx: SignTx | PrevTx,
        coin: coininfo.CoinInfo,
        sighash_type: int,
    ) -> bytes:
    """
    def preimage_hash(self, *args, **kwargs):
        # self.initialise(args[4]) # args[4] == tx
        return self.signature_digest(*args, **kwargs)

class Zip244HeaderHasher(Hasher):
    def __init__(self, tx):
        h = HashWriter(blake2b(outlen=32, personal=b'ZTxIdHeadersHash'))

        write_uint32(h, tx.version)           # T.1a: version             (4-byte little-endian version identifier including overwinter flag)
        write_uint32(h, tx.version_group_id)  # T.1b: version_group_id    (4-byte little-endian version group identifier)
        write_uint32(h, tx.branch_id)         # T.1c: consensus_branch_id (4-byte little-endian consensus branch id)
        write_uint32(h, tx.lock_time)         # T.1d: lock_time           (4-byte little-endian nLockTime value)
        write_uint32(h, tx.expiry)            # T.1e: expiry_height       (4-byte little-endian block height)

        self._digest = h.get_digest()

    def digest(self):
        return self._digest


class Zip244TransparentHasher(Hasher):
    def __init__(self):
        self.prevouts =      HashWriter(blake2b(outlen=32, personal=b'ZTxIdPrevoutHash'))
        self.amounts  =      HashWriter(blake2b(outlen=32, personal=b'ZTxTrAmountsHash'))
        self.scriptpubkeys = HashWriter(blake2b(outlen=32, personal=b'ZTxTrScriptsHash'))
        self.sequence =      HashWriter(blake2b(outlen=32, personal=b'ZTxIdSequencHash'))
        self.outputs  =      HashWriter(blake2b(outlen=32, personal=b'ZTxIdOutputsHash'))
        self.empty = True  # inputs_amount + outputs_amount == 0

    def add_input(self, txi: TxInput) -> None:
        self.empty = False
        write_bytes_reversed(self.prevouts, txi.prev_hash, 32)  # TODO: check this
        write_uint32(self.prevouts, txi.prev_index) 
        write_uint32(self.amounts, txi.amount)
        #write_uint32(self.scriptpubkeys, neco) # TODO
        write_uint32(self.sequence, txi.sequence)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self.empty = False
        write_tx_output(self.outputs, txo, script_pubkey)

    def digest(self):
        h = HashWriter(blake2b(outlen=32, personal=b'ZTxIdTranspaHash'))

        if not self.empty:
            write_hash(h, self.prevouts.get_digest())  # T.2a: prevouts_digest (32-byte hash)
            write_hash(h, self.sequence.get_digest())  # T.2b: sequence_digest (32-byte hash)
            write_hash(h, self.outputs.get_digest())   # T.2c: outputs_digest  (32-byte hash)

        return h.get_digest()

    def sig_digest(self, *args, **kwargs):
        if args == () and kwargs == {}: # Sapling Spend or Orchard Action
            txin_sig_digest = blake2b(outlen=32, personal=b'Zcash___TxInHash').digest()
        else: # transparent input
            txin_sig_digest = self.get_txin_sig_digest(*args, **kwargs)

        h = HashWriter(blake2b(outlen=32, personal=b'ZTxIdTranspaHash'))

        write_uint8(h, 0x01)                                 # S.2a: hash_type                (1 byte)
        write_hash(h, self.prevouts.get_digest())            # S.2b: prevouts_sig_digest      (32-byte hash)
        write_hash(h, self.amounts.get_digest())             # S.2c: amounts_sig_digest       (32-byte hash)
        write_hash(h, self.scriptpubkeys.get_digest())       # S.2d: scriptpubkeys_sig_digest (32-byte hash)
        write_hash(h, self.sequence.get_digest())            # S.2e: sequence_sig_digest      (32-byte hash)
        write_hash(h, self.outputs.get_digest())             # S.2f: outputs_sig_digest       (32-byte hash)
        write_hash(h, txin_sig_digest)                       # S.2g: txin_sig_digest          (32-byte hash)

        return h.get_digest()

    def get_txin_sig_digest(
        self,
        txi: TxInput,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        tx: SignTx | PrevTx, # no need for tx, TODO: = None
        coin: coininfo.CoinInfo,
        sighash_type: int,
    ):
        h = HashWriter(blake2b(outlen=32, personal=b'Zcash___TxInHash'))

        write_prevout(h, txi)                       # S.2d.i:   prevout     (field encoding)
        scripts.write_bip143_script_code_prefixed(  # S.2d.ii:  script_code (field encoding)
            h, txi, public_keys, threshold, coin
        )
        write_sint64(h, txi.amount)                 # S.2d.iii: value       (8-byte signed little-endian)
        write_uint32(h, txi.sequence)               # S.2d.iv:  nSequence   (4-byte unsigned little-endian)

        return h.get_digest()


class Zip244SaplingHasher(Hasher):
    # empty Sapling bundle

    def __init__(self):
        self.h = HashWriter(blake2b(outlen=32, personal=b"ZTxIdSaplingHash"))

    def digest(self):
        return self.h.get_digest()


class Zip244OrchardHasher(Hasher):
    def __init__(self):
        self.h  = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrchardHash"))
        self.ch = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrcActCHash"))
        self.mh = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrcActMHash"))
        self.nh = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOrcActNHash"))
        self.finalized = False
        self.empty = True # actions_amount == 0

    def add_action(self, action):
        assert not self.finalized
        self.empty = False
  
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
        assert not self.finalized
        if not self.empty:
            write_bytes_fixed(self.h, self.ch.get_digest(), 32)  # T.4a: orchard_actions_compact_digest      (32-byte hash output)
            write_bytes_fixed(self.h, self.mh.get_digest(), 32)  # T.4b: orchard_actions_memos_digest        (32-byte hash output)
            write_bytes_fixed(self.h, self.nh.get_digest(), 32)  # T.4c: orchard_actions_noncompact_digest   (32-byte hash output)
            write_bytes_fixed(self.h, flags, 1)                  # T.4d: flagsOrchard                        (1 byte)
            write_sint64(     self.h, value_balance)             # T.4e: valueBalanceOrchard                 (64-bit signed little-endian)
            write_bytes_fixed(self.h, anchor, 32)                # T.4f: anchorOrchard                       (32 bytes)

        self.finalized = True

    def digest(self):
        assert self.finalized
        return self.h.get_digest()
