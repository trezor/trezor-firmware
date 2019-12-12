from trezor.crypto.hashlib import sha3_256
from trezor.utils import HashWriter
from ubinascii import hexlify

from apps.nem2.transfer.layout import ask_transfer
from apps.nem2.mosaic.layout import ask_mosaic_definition, ask_mosaic_supply
from apps.nem2.namespace.layout import ask_namespace_registration, ask_address_alias, ask_mosaic_alias 
from apps.nem2.hash_lock.layout import ask_hash_lock
from apps.nem2.secret_lock.layout import ask_secret_lock

from apps.nem2.transfer.serialize import serialize_transfer
from apps.nem2.mosaic.serialize import serialize_mosaic_definition, serialize_mosaic_supply
from apps.nem2.namespace.serialize import serialize_namespace_registration, serialize_address_alias, serialize_mosaic_alias
from apps.nem2.hash_lock.serialize import serialize_hash_lock
from apps.nem2.secret_lock.serialize import serialize_secret_lock

from ..helpers import (
    NEM2_TRANSACTION_TYPE_TRANSFER,
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION,
    NEM2_TRANSACTION_TYPE_MOSAIC_SUPPLY,
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION,
    NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS,
    NEM2_TRANSACTION_TYPE_MOSAIC_ALIAS,
    NEM2_TRANSACTION_TYPE_HASH_LOCK,
    NEM2_TRANSACTION_TYPE_SECRET_LOCK
)

# Should be the key that maps to the transaction data
map_type_to_property = {
    NEM2_TRANSACTION_TYPE_TRANSFER: "transfer",
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION: "mosaic_definition",
    NEM2_TRANSACTION_TYPE_MOSAIC_SUPPLY: "mosaic_supply",
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION: "namespace_registration",
    NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS: "address_alias",
    NEM2_TRANSACTION_TYPE_MOSAIC_ALIAS: "mosaic_alias",
    NEM2_TRANSACTION_TYPE_HASH_LOCK: "hash_lock",
    NEM2_TRANSACTION_TYPE_SECRET_LOCK: "secret_lock"
}

map_type_to_serialize = {
    NEM2_TRANSACTION_TYPE_TRANSFER: serialize_transfer,
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION: serialize_mosaic_definition,
    NEM2_TRANSACTION_TYPE_MOSAIC_SUPPLY: serialize_mosaic_supply,
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION: serialize_namespace_registration,
    NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS: serialize_address_alias,
    NEM2_TRANSACTION_TYPE_MOSAIC_ALIAS: serialize_mosaic_alias,
    NEM2_TRANSACTION_TYPE_HASH_LOCK: serialize_hash_lock,
    NEM2_TRANSACTION_TYPE_SECRET_LOCK: serialize_secret_lock
}

map_type_to_layout = {
    NEM2_TRANSACTION_TYPE_TRANSFER: ask_transfer,
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION: ask_mosaic_definition,
    NEM2_TRANSACTION_TYPE_MOSAIC_SUPPLY: ask_mosaic_supply,
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION: ask_namespace_registration,
    NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS: ask_address_alias,
    NEM2_TRANSACTION_TYPE_MOSAIC_ALIAS: ask_mosaic_alias,
    NEM2_TRANSACTION_TYPE_HASH_LOCK: ask_hash_lock,
    NEM2_TRANSACTION_TYPE_SECRET_LOCK: ask_secret_lock
}

class MerkleTools(object):
    def __init__(self):
        self.reset_tree()

    def hash_function(self, s):
        # It just always use sha3_256
        # (no other hash algorithms are needed at this time)
        h = HashWriter(sha3_256())
        h.extend(s)
        return h

    def _to_hex(self, x):
        try:  # python3
            return x.hex()
        except:  # python2
            return hexlify(x)

    def reset_tree(self):
        self.leaves = list()
        self.levels = None
        self.is_ready = False

    def add_leaf(self, values, do_hash=False):
        self.is_ready = False
        # check if single leaf
        if not isinstance(values, tuple) and not isinstance(values, list):
            values = [values]
        for v in values:
            if do_hash:
                v = v.encode('utf-8')
                v = self.hash_function(v).get_digest()
            self.leaves.append(v)

    def get_leaf(self, index):
        return self._to_hex(self.leaves[index])

    def get_leaf_count(self):
        return len(self.leaves)

    def get_tree_ready_state(self):
        return self.is_ready

    def _calculate_next_level(self):
        solo_leave = None
        N = len(self.levels[0])  # number of leaves on the level
        if N % 2 == 1:  # if odd number of leaves on the level
            solo_leave = self.levels[0][-1]
            N -= 1

        new_level = []
        for l, r in zip(self.levels[0][0:N:2], self.levels[0][1:N:2]):
            new_level.append(self.hash_function(l+r).get_digest())
        if solo_leave is not None:
            new_level.append(solo_leave)
        self.levels = [new_level, ] + self.levels  # prepend new level

    def make_tree(self):
        self.is_ready = False
        if self.get_leaf_count() > 0:
            self.levels = [self.leaves, ]
            while len(self.levels[0]) > 1:
                self._calculate_next_level()
        self.is_ready = True

    def get_merkle_root(self):
        if self.is_ready:
            if self.levels is not None:
                return self._to_hex(self.levels[0][0])
            else:
                return None
        else:
            return None


    def get_merkle_root(self):
        if self.is_ready:
            if self.levels is not None:
                return self._to_hex(self.levels[0][0])
            else:
                return None
        else:
            return None
