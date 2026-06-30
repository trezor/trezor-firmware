from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .. import authdb
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session


@click.group(name="authdb")
def cli() -> None:
    """AuthDB commands – Sparse Merkle Tree root storage and proof verification."""


@cli.command()
@click.argument("root_hex")
@with_session
def set_root(session: "Session", root_hex: str) -> str:
    """Store a new Merkle root (32 bytes, hex-encoded) on the device."""
    root = bytes.fromhex(root_hex)
    counter = authdb.set_root(session, root)
    return f"Root stored. Counter: {counter}"


@cli.command()
@click.argument("address_hex")
@click.argument("value_hex")
@click.option(
    "-p",
    "--proof",
    "proof_hexes",
    multiple=True,
    help="Sibling hash (hex) at each level, leaf-to-root order.",
)
@with_session
def lookup(
    session: "Session",
    address_hex: str,
    value_hex: str,
    proof_hexes: tuple[str, ...],
) -> str:
    """Verify a Sparse Merkle Tree proof against the stored root.

    ADDRESS_HEX  hex-encoded address (key); its SHA-256 determines the tree path.
    VALUE_HEX    hex-encoded value stored at that address.

    Supply each sibling hash (hex, leaf-to-root) with -p <hex>.

    Example:
        trezorctl authdb lookup <addr_hex> <val_hex> -p <sib_leaf> -p <sib_root>
    """
    address = bytes.fromhex(address_hex)
    value = bytes.fromhex(value_hex)
    proof = [bytes.fromhex(h) for h in proof_hexes]
    valid, counter = authdb.lookup(session, address=address, value=value, proof=proof)
    status = "VALID" if valid else "INVALID"
    return f"Proof {status}. Counter: {counter}"
