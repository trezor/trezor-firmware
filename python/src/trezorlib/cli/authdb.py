from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .. import authdb
from ..merkle_tree import leaf_hash as mk_leaf_hash
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session


@click.group(name="authdb")
def cli() -> None:
    """AuthDB commands – Merkle-root storage and proof verification."""


@cli.command()
@click.argument("root_hex")
@with_session
def set_root(session: "Session", root_hex: str) -> str:
    """Store a new Merkle root (32 bytes, hex-encoded) on the device."""
    root = bytes.fromhex(root_hex)
    counter = authdb.set_root(session, root)
    return f"Root stored. Counter: {counter}"


@cli.command()
@click.argument("value_hex")
@click.option(
    "-p",
    "--proof",
    "proof_hexes",
    multiple=True,
    help="Sibling hash (hex) at each level, from leaf level to root.",
)
@with_session
def lookup(
    session: "Session",
    value_hex: str,
    proof_hexes: tuple[str, ...],
) -> str:
    """Verify a Merkle proof against the stored root.

    VALUE_HEX is the hex-encoded raw leaf value. Its leaf hash is computed
    automatically as SHA-256(0x00 || value).
    Supply each sibling hash (hex) with -p <hex>.

    Example:
        trezorctl authdb lookup <value_hex> -p <sib0> -p <sib1>
    """
    value = bytes.fromhex(value_hex)
    lhash = mk_leaf_hash(value)
    proof = [bytes.fromhex(h) for h in proof_hexes]
    valid, counter = authdb.lookup(session, leaf_hash=lhash, proof=proof)
    status = "VALID" if valid else "INVALID"
    return f"Proof {status}. Counter: {counter}"
