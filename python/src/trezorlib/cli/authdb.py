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
@click.option("--qm-counter", "qm_counter", type=int, required=True, help="Latest QM counter.")
@click.option(
    "--qm-signature",
    "qm_signature_hex",
    required=True,
    help="QM Ed25519 signature (hex) over b'AUTHDB QM v1'||wallet_id||counter(4B BE).",
)
@click.option("--root", "root_hex", default=None, help="Root from Evolu (hex); omit for a fresh wallet.")
@click.option("--counter", "counter", type=int, default=None, help="Counter the root was attested at.")
@click.option("--root-mac", "root_mac_hex", default=None, help="root_mac (hex) for the supplied root.")
@with_session
def init(
    session: "Session",
    qm_counter: int,
    qm_signature_hex: str,
    root_hex: str | None,
    counter: int | None,
    root_mac_hex: str | None,
) -> str:
    """Bootstrap the device AuthDB state from the QM counter + stored root.

    The device verifies the QM Ed25519 signature, stores qm_counter as the
    qm_last_counter anti-rollback ceiling, and — if a root is supplied —
    verifies counter == qm_counter and root_mac before installing it.
    """
    root = bytes.fromhex(root_hex) if root_hex else None
    root_mac = bytes.fromhex(root_mac_hex) if root_mac_hex else None
    qm_last, wallet_id, out_counter, out_root, out_mac = authdb.init(
        session,
        qm_counter=qm_counter,
        qm_signature=bytes.fromhex(qm_signature_hex),
        root=root,
        counter=counter,
        root_mac=root_mac,
    )
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    root_out = out_root.hex() if out_root else "(empty)"
    mac_out = out_mac.hex() if out_mac else "(none)"
    return (
        f"Initialized. QM last counter: {qm_last}. Wallet ID: {id_hex}. "
        f"Counter: {out_counter}. Root: {root_out}. Root-MAC: {mac_out}"
    )


@cli.command(name="set-root")
@click.argument("root_hex")
@click.option("--mac", "mac_hex", default=None, help="Root-attestation MAC (hex) from update-leaf.")
@click.option("--wallet-id", "wallet_id_hex", default=None, help="Wallet ID (hex); required with a real mac.")
@click.option("--counter", "counter", type=int, default=None, help="Target counter; required with a real mac.")
@with_session
def set_root(
    session: "Session",
    root_hex: str,
    mac_hex: str | None,
    wallet_id_hex: str | None,
    counter: int | None,
) -> str:
    """Install a Merkle root (32 bytes, hex-encoded) on the device.

    With no --mac this is a debug-only unauthenticated injection. Supply
    --mac (a device-produced root-attestation token) plus --wallet-id and
    --counter for the production-safe, MAC-verified path.
    """
    root = bytes.fromhex(root_hex)
    mac = bytes.fromhex(mac_hex) if mac_hex else None
    wallet_id_arg = bytes.fromhex(wallet_id_hex) if wallet_id_hex else None
    out_counter, wallet_id, new_root, root_mac = authdb.set_root(
        session, root, mac=mac, wallet_id=wallet_id_arg, counter=counter
    )
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    mac_out = root_mac.hex() if root_mac else "(none)"
    return f"Root stored. Counter: {out_counter}. Wallet ID: {id_hex}. Root-MAC: {mac_out}"


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
@click.option("--counter", "counter", type=int, default=None, help="Leaf counter for a membership proof.")
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
@click.option(
    "--witness-counter",
    "witness_counter",
    type=int,
    default=None,
    help="Witness leaf counter for non-membership proof.",
)
@with_session
def lookup(
    session: "Session",
    address_hex: str,
    value_hex: str,
    proof_hexes: tuple[str, ...],
    counter: int | None,
    witness_address_hex: str | None,
    witness_value_hex: str | None,
    witness_counter: int | None,
) -> str:
    """Verify an MPT proof against the stored root.

    ADDRESS_HEX  hex-encoded address (key).
    VALUE_HEX    hex-encoded value (required for membership proof; omit for non-membership).

    For a membership proof:
        trezorctl authdb lookup <addr_hex> <val_hex> --counter <n> -p <sib1> ...

    For a non-membership proof:
        trezorctl authdb lookup <addr_hex> -p <sib1> ... \\
            --witness-address <w_addr_hex> --witness-value <w_val_hex> --witness-counter <n>
    """
    address = bytes.fromhex(address_hex)
    value = bytes.fromhex(value_hex) if value_hex else None
    proof = [bytes.fromhex(h) for h in proof_hexes]
    witness_address = bytes.fromhex(witness_address_hex) if witness_address_hex else None
    witness_value = bytes.fromhex(witness_value_hex) if witness_value_hex else None

    valid, membership, out_counter, wallet_id = authdb.lookup(
        session,
        address=address,
        value=value,
        proof=proof,
        counter=counter,
        witness_address=witness_address,
        witness_value=witness_value,
        witness_counter=witness_counter,
    )
    proof_type = "membership" if membership else "non-membership"
    status = "VALID" if valid else "INVALID"
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    return f"Proof {status} ({proof_type}). Counter: {out_counter}. Wallet ID: {id_hex}"


@cli.command(name="update-leaf")
@click.argument("address_hex")
@click.argument("old_value_hex")
@click.argument("new_value_hex")
@click.option(
    "--new-counter",
    "new_counter",
    type=int,
    required=True,
    help="New global counter to stamp the leaf with (current root counter + 1).",
)
@click.option(
    "--old-counter",
    "old_counter",
    type=int,
    default=None,
    help="The leaf's previous global stamp (UPDATE/DELETE).",
)
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
    "--witness-counter",
    "witness_counter",
    type=int,
    default=None,
    help="Witness leaf counter for INSERT non-membership proof.",
)
@with_session
def update_leaf(
    session: "Session",
    address_hex: str,
    old_value_hex: str,
    new_value_hex: str,
    new_counter: int,
    old_counter: int | None,
    proof_hexes: tuple[str, ...],
    witness_address_hex: str | None,
    witness_value_hex: str | None,
    witness_counter: int | None,
) -> str:
    """Atomically update a leaf in the Merkle tree.

    \b
    Operations (determined by old/new values):
      UPDATE  old_value non-empty, new_value non-empty  – membership proof
      DELETE  old_value non-empty, new_value ""         – membership proof
      INSERT  old_value "",        new_value non-empty  – non-membership proof
      INIT    old_value "",        new_value non-empty  – no proof, empty tree

    Pass "" (empty string) for old_value when inserting, or for new_value when deleting.
    --new-counter must equal the current root counter + 1 (global-counter model).
    """
    address = bytes.fromhex(address_hex)
    old_value = bytes.fromhex(old_value_hex) if old_value_hex else b""
    new_value = bytes.fromhex(new_value_hex) if new_value_hex else b""
    proof = [bytes.fromhex(h) for h in proof_hexes]
    witness_address = bytes.fromhex(witness_address_hex) if witness_address_hex else None
    witness_value = bytes.fromhex(witness_value_hex) if witness_value_hex else None

    counter, new_root, wallet_id, new_mac = authdb.update_leaf(
        session,
        address=address,
        old_value=old_value,
        new_value=new_value,
        new_counter=new_counter,
        old_counter=old_counter,
        proof=proof,
        witness_address=witness_address,
        witness_value=witness_value,
        witness_counter=witness_counter,
    )
    root_hex = new_root.hex() if new_root else "(empty)"
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    mac_out = new_mac.hex() if new_mac else "(none)"
    return f"Updated. Counter: {counter}. New root: {root_hex}. Wallet ID: {id_hex}. MAC: {mac_out}"


@cli.command()
@click.argument("address_hex")
@click.argument("old_value_hex")
@click.option(
    "--new-counter",
    "new_counter",
    type=int,
    required=True,
    help="New global counter to stamp (current root counter + 1).",
)
@click.option(
    "--old-counter",
    "old_counter",
    type=int,
    default=None,
    help="The leaf's previous global stamp.",
)
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
    new_counter: int,
    old_counter: int | None,
    proof_hexes: tuple[str, ...],
) -> str:
    """Delete an entry from the Merkle tree.

    Equivalent to update-leaf <addr> <old_val> "" --new-counter <n> [-p ...].
    """
    address = bytes.fromhex(address_hex)
    old_value = bytes.fromhex(old_value_hex)
    proof = [bytes.fromhex(h) for h in proof_hexes]

    counter, new_root, wallet_id, _mac = authdb.update_leaf(
        session,
        address=address,
        old_value=old_value,
        new_value=b"",
        new_counter=new_counter,
        old_counter=old_counter,
        proof=proof,
    )
    root_hex = new_root.hex() if new_root else "(empty)"
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    return f"Deleted. Counter: {counter}. New root: {root_hex}. Wallet ID: {id_hex}"
