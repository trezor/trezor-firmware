from typing import TYPE_CHECKING

from trezor.crypto import bip32
from trezor.crypto.hashlib import sha256
from trezorminiscript import collect_keys

if TYPE_CHECKING:
    from trezor.messages import (
        MiniscriptDerivation,
        MiniscriptKey,
        MiniscriptPolicy,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


def derive_node(key: MiniscriptKey, *public_indices: int) -> bip32.HDNode:
    # Miniscript nodes use only secp256k1 curve.
    node = key.node
    node = bip32.HDNode(
        depth=node.depth,
        fingerprint=node.fingerprint,
        child_num=node.child_num,
        chain_code=node.chain_code,
        public_key=node.public_key,
    )
    for idx in public_indices:
        node.derive(idx, True)
    return node


def validate_policy(
    policy: MiniscriptPolicy, keychain: Keychain, coin: CoinInfo
) -> None:
    if not policy.keys:
        raise ValueError  # no keys provided

    xpubs = [derive_node(key).serialize_public(coin.xpub_magic) for key in policy.keys]
    if len(xpubs) != len(set(xpubs)):
        raise ValueError  # duplicate xpubs

    if not (key_exprs := collect_keys(policy.descriptor)):
        raise ValueError  # no keys found in descriptor

    # keep a set of child indices for each key
    children_per_key = [set() for _ in policy.keys]

    max_key_idx = 0
    for key_idx, *children in key_exprs:
        if key_idx > max_key_idx:
            # enforce canonical ordering of key indices
            if key_idx != max_key_idx + 1:
                raise ValueError
            max_key_idx = key_idx

        key_children = children_per_key[key_idx]
        if len(children) != 2:
            raise ValueError

        for child_idx in children:
            if child_idx in key_children:
                raise ValueError  # duplicate child index
            if not 0 <= child_idx < 10:
                raise ValueError  # child index out of range
            key_children.add(child_idx)

    if not all(children_per_key):
        raise ValueError  # all keys must be used

    own_key = policy.keys[policy.own_index]
    if own_key.root_fingerprint != keychain.root_fingerprint():
        raise ValueError

    own_path = own_key.derivation_path
    for child in children_per_key[policy.own_index]:
        # check that all children can be derived and the public keys match the provided xpub
        first_child = [child, 0]
        own_pubkey = keychain.derive(own_path + first_child).public_key()
        if own_pubkey != derive_node(own_key, *first_child).public_key():
            raise ValueError


def _digest_policy(policy: MiniscriptPolicy) -> bytes:
    from trezor.protobuf import dump_message_buffer

    return sha256(dump_message_buffer(policy)).digest()


class RegisteredPolicy:
    def __init__(self, policy: MiniscriptPolicy, name: str) -> None:
        """MUST be constructed using `load_policy()` below."""
        self._policy = policy
        self.name = name

    def script_wsh(self, derivation: MiniscriptDerivation) -> bytes:
        from trezorminiscript import compile

        keys = self._policy.keys

        def _derive_fn(key_idx: int, *children: int) -> bytes:
            # Raises ValueError on invalid input:
            if len(children) != 2:
                raise ValueError

            child_idx = children[derivation.internal]
            return derive_node(keys[key_idx], child_idx, derivation.index).public_key()

        return compile(self._policy.descriptor, _derive_fn)

    def address_wsh(self, derivation: MiniscriptDerivation, coin: CoinInfo) -> str:
        if coin.bech32_prefix is None:
            raise ValueError  # Unsupported coin

        # TODO: make sure our key is included
        # TODO: better `wsh()` enforcement?
        if self._policy.descriptor.startswith("wsh("):
            # TODO: remove _ prefix
            from ..addresses import _address_p2wsh

            return _address_p2wsh(
                sha256(self.script_wsh(derivation)).digest(),
                coin.bech32_prefix,
            )

        # TODO: only `wsh()` is supported
        raise ValueError  # Unsupported descriptor


async def store_policy(policy: MiniscriptPolicy, name: str) -> None:
    from storage.device import set_registered_miniscript
    from trezor.messages import MiniscriptRegisteredEntry
    from trezor.protobuf import dump_message_buffer

    entry = MiniscriptRegisteredEntry(
        policy_digest=_digest_policy(policy),
        # TODO: keep more details (e.g. change indices for owned keys)
        name=name,
    )
    set_registered_miniscript(dump_message_buffer(entry))


async def load_policy(policy: MiniscriptPolicy) -> RegisteredPolicy:
    from storage.device import get_registered_miniscript
    from trezor.messages import MiniscriptRegisteredEntry
    from trezor.protobuf import decode

    if (buf := get_registered_miniscript()) is not None:
        # TODO: experimental protobuf marker
        entry = decode(buf, MiniscriptRegisteredEntry, True)
        if entry.policy_digest == _digest_policy(policy):
            return RegisteredPolicy(policy, entry.name)

    from trezor.wire import ProcessError

    raise ProcessError("Unregistered policy")
