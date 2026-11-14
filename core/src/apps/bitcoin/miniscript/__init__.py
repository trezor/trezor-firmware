# TODO: exclude if USE_MINISCRIPT=0

from typing import TYPE_CHECKING

from trezor.crypto import bip32
from trezor.crypto.hashlib import sha256
from trezor.messages import MiniscriptRegisteredInfo
from trezor.protobuf import dump_message_buffer
from trezor.wire import DataError, ProcessError
from trezorminiscript import collect_keys

if TYPE_CHECKING:
    from trezor.messages import (
        MiniscriptDerivation,
        MiniscriptKey,
        MiniscriptPolicy,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain
    from apps.ward import WardStore


# TODO: make it DataError
class InvalidPolicy(ValueError):
    pass


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
    keychain: Keychain, coin: CoinInfo, policy: MiniscriptPolicy, name: str
) -> MiniscriptRegisteredInfo:
    from ..common import BITCOIN_NAMES

    if coin.coin_name not in BITCOIN_NAMES:
        raise DataError("Unsupported coin")

    if not name:
        # TODO: more checks (i.e. no duplicates, avoid whitespace, etc.)
        raise InvalidPolicy

    if not policy.keys:
        raise InvalidPolicy  # no keys provided

    public_keys = (derive_node(key).public_key() for key in policy.keys)
    if len(set(public_keys)) != len(policy.keys):
        raise InvalidPolicy  # public keys must be unique

    if not (key_exprs := collect_keys(policy.descriptor)):
        raise InvalidPolicy  # no keys found in descriptor

    # Detect duplicate child indices (per key expression)
    children_per_key = [set() for _ in policy.keys]
    next_key_idx = 0
    for key_idx, *children in key_exprs:
        if key_idx >= len(policy.keys):
            raise InvalidPolicy  # key index out of range

        if key_idx > next_key_idx:
            raise InvalidPolicy  # enforce canonical ordering of key indices
        elif key_idx == next_key_idx:
            next_key_idx += 1

        key_children = children_per_key[key_idx]
        if len(children) != 2:
            raise InvalidPolicy

        for child_idx in children:
            if child_idx in key_children:
                raise InvalidPolicy  # duplicate child index
            if not 0 <= child_idx < 10:
                raise InvalidPolicy  # child index out of range
            key_children.add(child_idx)

    if not all(children_per_key):
        raise InvalidPolicy  # all keys must be used

    own_key = policy.keys[policy.own_index]
    if own_key.root_fingerprint != keychain.root_fingerprint():
        raise InvalidPolicy

    own_derivation_path = own_key.derivation_path
    children = children_per_key[policy.own_index]

    def _to_xpub(node: bip32.HDNode) -> str:
        return node.serialize_public(coin.xpub_magic)

    for child_idx in children:
        # 1. check that all derivation paths are valid
        # 2. compare own node with provided one
        # TODO: allow only BIP-48 paths?
        first_child = [child_idx, 0]
        own = keychain.derive(own_derivation_path + first_child)
        if _to_xpub(own) != _to_xpub(derive_node(own_key, *first_child)):
            raise InvalidPolicy

    return MiniscriptRegisteredInfo(name=name, children=sorted(children))


class RegisteredPolicy:
    def __init__(
        self, policy: MiniscriptPolicy, info: MiniscriptRegisteredInfo
    ) -> None:
        """MUST be constructed using `load_policy()` below."""
        self.policy = policy
        self.info = info

    def script_wsh(self, derivation: MiniscriptDerivation) -> bytes:
        from trezorminiscript import compile

        keys = self.policy.keys

        def _derive_fn(key_idx: int, *children: int) -> bytes:
            # Raises ValueError on invalid input:
            if len(children) != 2:
                raise RuntimeError

            child_idx = children[derivation.internal]
            return derive_node(keys[key_idx], child_idx, derivation.index).public_key()

        return compile(self.policy.descriptor, _derive_fn)

    def address_wsh(self, derivation: MiniscriptDerivation, coin: CoinInfo) -> str:
        if coin.bech32_prefix is None:
            raise ValueError  # Unsupported coin

        # TODO: make sure our key is included
        # TODO: better `wsh()` enforcement?
        if self.policy.descriptor.startswith("wsh("):
            # TODO: remove _ prefix
            from ..addresses import _address_p2wsh

            return _address_p2wsh(
                sha256(self.script_wsh(derivation)).digest(),
                coin.bech32_prefix,
            )

        # TODO: only `wsh()` is supported
        raise DataError("Unsupported descriptor")  # Unsupported descriptor


async def store_policy(
    ward: WardStore,
    coin: CoinInfo,
    policy: MiniscriptPolicy,
    info: MiniscriptRegisteredInfo,
) -> None:
    ward = ward.subscope(coin.coin_name.encode())
    key = dump_message_buffer(policy)
    value = dump_message_buffer(info)
    await ward.set(key, value)


async def load_policy(
    ward: WardStore, coin: CoinInfo, policy: MiniscriptPolicy
) -> RegisteredPolicy:
    ward = ward.subscope(coin.coin_name.encode())
    key = dump_message_buffer(policy)
    if (value := await ward.get(key)) is None:
        raise ProcessError("Unregistered policy")

    from trezor.protobuf import decode

    info = decode(value, MiniscriptRegisteredInfo, True)  # True: info is experimental
    return RegisteredPolicy(policy, info)
