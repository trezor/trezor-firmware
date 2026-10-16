from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import HDNodeType, MiniscriptRedeemPolicyType

import trezorminiscript
from trezor.crypto import bip32


def _trim(s: str, prefix: str, suffix: str) -> str:
    if not s.startswith(prefix) or not s.endswith(suffix):
        raise ValueError
    return s[len(prefix) : -len(suffix)]


def derive_node(n: HDNodeType, change: int, index: int) -> bip32.HDNode:
    # Miniscript nodes use only secp256k1 curve.
    node = bip32.HDNode(
        depth=n.depth,
        fingerprint=n.fingerprint,
        child_num=n.child_num,
        chain_code=n.chain_code,
        public_key=n.public_key,
    )
    # `True` = public child key derivation
    node.derive(change, True)
    node.derive(index, True)
    return node


def _parse_index(s: str) -> int:
    # TODO: check for non-canonical representations
    return int(s)

def compile_internal(derivation: MiniscriptRedeemPolicyType) -> bytes:
    """Don't use this function directly; use `scripts.derive_miniscript()` instead to ensure the policy is registered."""

    policy = derivation.policy
    keys = policy.keys
    used = [False] * len(keys)  # all keys must be used by the policy

    def _derive_fn(key_expr: str) -> bytes:
        # KEY expression must be "@N/<I;J>/*"
        # Raises ValueError on invalid input:
        key_idx, children = _trim(key_expr, "@", "/*").split("/")
        key_idx = _parse_index(key_idx)

        external_idx, internal_idx = _trim(children, "<", ">").split(";")
        external_idx = _parse_index(external_idx)
        internal_idx = _parse_index(internal_idx)
        child_idx = (external_idx, internal_idx)[derivation.internal]

        if 0 <= key_idx < len(keys):
            node = keys[key_idx].node
            pubkey = derive_node(node, child_idx, derivation.index).public_key()
            used[key_idx] = True
            return pubkey

        raise ValueError

    script = trezorminiscript.compile(policy.descriptor, _derive_fn)
    if not all(used):
        raise ValueError

    return script
