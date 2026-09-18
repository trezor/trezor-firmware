from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import HDNodeType, MiniscriptRedeemPolicyType

import trezorminiscript
from trezor.crypto import bip32


def _trim(s: str, prefix: str, suffix: str) -> str:
    if not s.startswith(prefix) or not s.endswith(suffix):
        raise ValueError
    return s[len(prefix) : -len(suffix)]


def parse_nodes(nodes: list[HDNodeType]) -> list[bip32.HDNode]:
    # Miniscript nodes use only secp256k1 curve.
    return [
        bip32.HDNode(
            depth=n.depth,
            fingerprint=n.fingerprint,
            child_num=n.child_num,
            chain_code=n.chain_code,
            public_key=n.public_key,
        )
        for n in nodes
    ]


def compile(derivation: MiniscriptRedeemPolicyType) -> bytes:
    """Don't use this function directly; use derive_miniscript() instead to ensure the policy is registered."""

    policy = derivation.policy
    nodes = parse_nodes(policy.nodes)
    used = [False] * len(nodes)  # all keys must be used by the policy

    def _derive_fn(key: str) -> bytes:
        # KEY expression must be "@N/<I;J>/*"
        # Raises ValueError on invalid input:
        key_idx, children = _trim(key, "@", "/*").split("/")
        external_idx, internal_idx = _trim(children, "<", ">").split(";")
        child_idx = int((external_idx, internal_idx)[derivation.internal])
        key_idx = int(key_idx)

        if 0 <= key_idx < len(nodes):
            node = nodes[key_idx].clone()  # since BIP-32 derivation is done in-place
            node.derive(child_idx, True)
            node.derive(derivation.index, True)
            used[key_idx] = True
            return node.public_key()

        raise ValueError

    script = trezorminiscript.compile(policy.descriptor, _derive_fn)
    if not all(used):
        raise ValueError

    return script
