from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .. import authdb
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session


@click.group(name="authdb")
def cli() -> None:
    """AuthDB commands – Merkle Patricia Trie root storage and proof verification."""


@cli.command()
@click.argument("root_hex")
@with_session
def set_root(session: "Session", root_hex: str) -> str:
    """Store a new Merkle root (32 bytes, hex-encoded) on the device.

    DEBUG BUILDS ONLY.  On production firmware the root is derived by the
    device itself via the update-leaf command.
    """
    root = bytes.fromhex(root_hex)
    counter, identifier = authdb.set_root(session, root)
    id_hex = identifier.hex() if identifier else "(none)"
    return f"Root stored. Counter: {counter}. Identifier: {id_hex}"


@cli.command()
@click.argument("address_hex")
@click.argument("value_hex", default="", required=False)
@click.option(
    "-p",
    "--proof",
    "proof_hexes",
    multiple=True,
    help="Sibling hash (hex, 33 bytes) at each level, leaf-to-root order.",
)
@click.option(
    "--witness-address",
    "witness_address_hex",
    default=None,
    help="Witness address (hex) for non-membership proof.",
)
@click.option(
    "--witness-value",
    "witness_value_hex",
    default=None,
    help="Witness value (hex) for non-membership proof.",
)
@with_session
def lookup(
    session: "Session",
    address_hex: str,
    value_hex: str,
    proof_hexes: tuple[str, ...],
    witness_address_hex: str | None,
    witness_value_hex: str | None,
) -> str:
    """Verify an MPT proof against the stored root.

    ADDRESS_HEX  hex-encoded address (key).
    VALUE_HEX    hex-encoded value (required for membership proof; omit for non-membership).

    For a membership proof:
        trezorctl authdb lookup <addr_hex> <val_hex> -p <sib1> -p <sib2> ...

    For a non-membership proof:
        trezorctl authdb lookup <addr_hex> -p <sib1> ... \\
            --witness-address <w_addr_hex> --witness-value <w_val_hex>
    """
    address = bytes.fromhex(address_hex)
    value = bytes.fromhex(value_hex) if value_hex else None
    proof = [bytes.fromhex(h) for h in proof_hexes]
    witness_address = bytes.fromhex(witness_address_hex) if witness_address_hex else None
    witness_value = bytes.fromhex(witness_value_hex) if witness_value_hex else None

    valid, membership, counter, identifier = authdb.lookup(
        session,
        address=address,
        value=value,
        proof=proof,
        witness_address=witness_address,
        witness_value=witness_value,
    )
    proof_type = "membership" if membership else "non-membership"
    status = "VALID" if valid else "INVALID"
    id_hex = identifier.hex() if identifier else "(none)"
    return f"Proof {status} ({proof_type}). Counter: {counter}. Identifier: {id_hex}"


@cli.command(name="update-leaf")
@click.argument("address_hex")
@click.argument("old_value_hex")
@click.argument("new_value_hex")
@click.option(
    "-p",
    "--proof",
    "proof_hexes",
    multiple=True,
    help="Sibling hash (hex, 33 bytes) at each level, leaf-to-root order.",
)
@click.option(
    "--witness-address",
    "witness_address_hex",
    default=None,
    help="Witness address (hex) for INSERT non-membership proof.",
)
@click.option(
    "--witness-value",
    "witness_value_hex",
    default=None,
    help="Witness value (hex) for INSERT non-membership proof.",
)
@click.option(
    "--mac",
    "mac_hex",
    default=None,
    help="MAC token (hex) from a prior approve call — skips confirmation dialog.",
)
@click.option(
    "--device-id",
    "device_id_hex",
    default=None,
    help="Device identifier (hex) matching the MAC token.",
)
@with_session
def update_leaf(
    session: "Session",
    address_hex: str,
    old_value_hex: str,
    new_value_hex: str,
    proof_hexes: tuple[str, ...],
    witness_address_hex: str | None,
    witness_value_hex: str | None,
    mac_hex: str | None,
    device_id_hex: str | None,
) -> str:
    """Atomically update a leaf in the Merkle tree.

    \b
    Operations (determined by old/new values):
      UPDATE  old_value non-empty, new_value non-empty  – membership proof
      DELETE  old_value non-empty, new_value ""         – membership proof
      INSERT  old_value "",        new_value non-empty  – non-membership proof
      INIT    old_value "",        new_value non-empty  – no proof, empty tree

    Pass "" (empty string) for old_value when inserting, or for new_value when deleting.

    \b
    Examples:
      # UPDATE alice's value:
      trezorctl authdb update-leaf <addr_hex> <old_hex> <new_hex> -p <sib> ...

      # DELETE alice:
      trezorctl authdb update-leaf <addr_hex> <old_hex> "" -p <sib> ...

      # INSERT into existing tree (supply witness from non-membership proof):
      trezorctl authdb update-leaf <addr_hex> "" <new_hex> -p <sib> ... \\
          --witness-address <w_addr_hex> --witness-value <w_val_hex>

      # INIT (first entry, tree was empty):
      trezorctl authdb update-leaf <addr_hex> "" <new_hex>
    """
    address = bytes.fromhex(address_hex)
    old_value = bytes.fromhex(old_value_hex) if old_value_hex else b""
    new_value = bytes.fromhex(new_value_hex) if new_value_hex else b""
    proof = [bytes.fromhex(h) for h in proof_hexes]
    witness_address = bytes.fromhex(witness_address_hex) if witness_address_hex else None
    witness_value = bytes.fromhex(witness_value_hex) if witness_value_hex else None
    mac = bytes.fromhex(mac_hex) if mac_hex else None
    device_id = bytes.fromhex(device_id_hex) if device_id_hex else None

    counter, new_root, identifier, new_mac, auth_mac = authdb.update_leaf(
        session,
        address=address,
        old_value=old_value,
        new_value=new_value,
        proof=proof,
        witness_address=witness_address,
        witness_value=witness_value,
        mac=mac,
        device_id=device_id,
    )
    root_hex = new_root.hex() if new_root else "(empty)"
    id_hex = identifier.hex() if identifier else "(none)"
    mac_out = new_mac.hex() if new_mac else "(none)"
    auth_mac_out = auth_mac.hex() if auth_mac else "(none)"
    return f"Updated. Counter: {counter}. New root: {root_hex}. Identifier: {id_hex}. MAC: {mac_out}. Auth-MAC: {auth_mac_out}"


@cli.command(name="clear-root")
@with_session
def clear_root(session: "Session") -> str:
    """Wipe the stored Merkle root and bump the counter. DEBUG BUILDS ONLY."""
    identifier = authdb.clear_root(session)
    id_hex = identifier.hex() if identifier else "(none)"
    return f"Root cleared. Identifier: {id_hex}"


@cli.command()
@click.argument("address_hex")
@click.argument("old_value_hex")
@click.option(
    "-p",
    "--proof",
    "proof_hexes",
    multiple=True,
    help="Sibling hash (hex, 33 bytes) at each level, leaf-to-root order.",
)
@with_session
def delete(
    session: "Session",
    address_hex: str,
    old_value_hex: str,
    proof_hexes: tuple[str, ...],
) -> str:
    """Delete an entry from the Merkle tree.

    Equivalent to update-leaf <addr> <old_val> "" [-p ...].

    ADDRESS_HEX    hex-encoded address to delete.
    OLD_VALUE_HEX  hex-encoded current value (required to prove membership).
    """
    address = bytes.fromhex(address_hex)
    old_value = bytes.fromhex(old_value_hex)
    proof = [bytes.fromhex(h) for h in proof_hexes]

    counter, new_root, identifier, _mac, _auth_mac = authdb.update_leaf(
        session,
        address=address,
        old_value=old_value,
        new_value=b"",
        proof=proof,
    )
    root_hex = new_root.hex() if new_root else "(empty)"
    id_hex = identifier.hex() if identifier else "(none)"
    return f"Deleted. Counter: {counter}. New root: {root_hex}. Identifier: {id_hex}"


@cli.command()
@click.argument("address_hex")
@click.argument("value_hex")
@with_session
def approve(session: "Session", address_hex: str, value_hex: str) -> str:
    """Pre-authorize an (address, value) pair on the device.

    The user confirms on-screen; the device returns a MAC token.
    Use the returned MAC with update-leaf --mac to skip future confirmation dialogs.

    ADDRESS_HEX  hex-encoded address to authorize.
    VALUE_HEX    hex-encoded value to authorize at that address.
    """
    address = bytes.fromhex(address_hex)
    value = bytes.fromhex(value_hex)
    mac, identifier = authdb.approve(session, address=address, value=value)
    mac_hex = mac.hex()
    id_hex = identifier.hex() if identifier else "(none)"
    return f"Approved. MAC: {mac_hex}. Identifier: {id_hex}"
