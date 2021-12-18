from trezor.crypto.hashlib import blake2b
from trezor.utils import HashWriter

ZCASH_ORCHARD_HASH_PERSONALIZATION = b"ZTxIdOrchardHash";
ZCASH_ORCHARD_ACTIONS_COMPACT_HASH_PERSONALIZATION = b"ZTxIdOrcActCHash";
ZCASH_ORCHARD_ACTIONS_MEMOS_HASH_PERSONALIZATION = b"ZTxIdOrcActMHash";
ZCASH_ORCHARD_ACTIONS_NONCOMPACT_HASH_PERSONALIZATION: = b"ZTxIdOrcActNHash";
ZCASH_ORCHARD_SIGS_HASH_PERSONALIZATION = b"ZTxAuthOrchaHash";

class ZIP244OrchardHasher:
    def __init__(self):
        self.ch = HashWriter(blake2b(outlen=32, personal=ZCASH_ORCHARD_ACTIONS_COMPACT_HASH_PERSONALIZATION))
        self.mh = HashWriter(blake2b(outlen=32, personal=ZCASH_ORCHARD_ACTIONS_MEMOS_HASH_PERSONALIZATION))
        self.nh = HashWriter(blake2b(outlen=32, personal=ZCASH_ORCHARD_ACTIONS_NONCOMPACT_HASH_PERSONALIZATION))

    def update(self, action):
        write_bytes_fixed(self.ch, action["nullifier"], 32)
        write_bytes_fixed(self.ch, action["cmx"], 32)
        write_bytes_fixed(self.ch, action["epk"], 32)
        write_bytes_fixed(self.ch, action["enc_ciphertext"][:52], 52)

        write_bytes_fixed(self.mh, action["enc_ciphertext"][52:564], 512)

        write_bytes_fixed(self.nh, action["cv_net"], 32)
        write_bytes_fixed(self.nh, action["rk"], 32);
        write_bytes_fixed(self.nh, action["enc_ciphertext"][564:], 16)
        write_bytes_fixed(self.nh, action["out_ciphertext"], 80)

    def finalize(self, flags, value_balance, anchor):
        h = HashWriter(blake2b(outlen=32, personal=ZCASH_ORCHARD_HASH_PERSONALIZATION))
        write_bytes_fixed(h, self.ch.finalize(), 32)
        write_bytes_fixed(h, self.mh.finalize(), 32)
        write_bytes_fixed(h, self.nh.finalize(), 32)
        write_bytes_fixed(h, flags, 1)
        write_bytes_fixed(h, value_balance, 8)
        write_bytes_fixed(h, anchor, 32)
        h.finalize()
