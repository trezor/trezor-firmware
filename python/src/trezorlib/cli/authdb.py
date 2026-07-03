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
    counter, wallet_id = authdb.set_root(session, root)
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    return f"Root stored. Counter: {counter}. Wallet ID: {id_hex}"


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

    valid, membership, counter, wallet_id = authdb.lookup(
        session,
        address=address,
        value=value,
        proof=proof,
        witness_address=witness_address,
        witness_value=witness_value,
    )
    proof_type = "membership" if membership else "non-membership"
    status = "VALID" if valid else "INVALID"
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    return f"Proof {status} ({proof_type}). Counter: {counter}. Wallet ID: {id_hex}"


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

    counter, new_root, wallet_id, new_mac, auth_mac = authdb.update_leaf(
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
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    mac_out = new_mac.hex() if new_mac else "(none)"
    auth_mac_out = auth_mac.hex() if auth_mac else "(none)"
    return f"Updated. Counter: {counter}. New root: {root_hex}. Wallet ID: {id_hex}. MAC: {mac_out}. Auth-MAC: {auth_mac_out}"


@cli.command(name="clear-root")
@with_session
def clear_root(session: "Session") -> str:
    """Wipe the stored Merkle root and bump the counter. DEBUG BUILDS ONLY."""
    wallet_id = authdb.clear_root(session)
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    return f"Root cleared. Wallet ID: {id_hex}"


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

    counter, new_root, wallet_id, _mac, _auth_mac = authdb.update_leaf(
        session,
        address=address,
        old_value=old_value,
        new_value=b"",
        proof=proof,
    )
    root_hex = new_root.hex() if new_root else "(empty)"
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    return f"Deleted. Counter: {counter}. New root: {root_hex}. Wallet ID: {id_hex}"


@cli.command()
@click.argument("address_hex")
@click.argument("old_value_hex")
@click.argument("new_value_hex")
@with_session
def approve(session: "Session", address_hex: str, old_value_hex: str, new_value_hex: str) -> str:
    """Pre-authorize an address old_value->new_value transition on the device.

    The user confirms on-screen; the device returns a MAC token computed the
    same way update-leaf verifies it. Use the returned MAC with update-leaf
    --mac (for this exact address/old_value/new_value) to skip future
    confirmation dialogs.

    ADDRESS_HEX    hex-encoded address to authorize.
    OLD_VALUE_HEX  hex-encoded current value; "" if the address is absent (INSERT/INIT).
    NEW_VALUE_HEX  hex-encoded value to authorize at that address.
    """
    address = bytes.fromhex(address_hex)
    old_value = bytes.fromhex(old_value_hex) if old_value_hex else None
    new_value = bytes.fromhex(new_value_hex)
    mac, wallet_id = authdb.approve(session, address=address, new_value=new_value, old_value=old_value)
    mac_hex = mac.hex()
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    return f"Approved. MAC: {mac_hex}. Wallet ID: {id_hex}"


@cli.command(name="set-cache-entry")
@click.argument("address_hex")
@click.option("--label", "label", default=None, help="Human-readable label for the address.")
@click.option("--data-mac", "data_mac_hex", default=None, help="MAC authorizing the data field (hex).")
@with_session
def set_cache_entry(
    session: "Session",
    address_hex: str,
    label: str | None,
    data_mac_hex: str | None,
) -> str:
    """Store offline-cache metadata (label and/or data_mac) for an address.

    ADDRESS_HEX  hex-encoded address key.
    """
    address = bytes.fromhex(address_hex)
    data_mac = bytes.fromhex(data_mac_hex) if data_mac_hex else None
    identifier_crc = authdb.set_cache_entry(session, address=address, label=label, data_mac=data_mac)
    return f"Cache entry stored. Identifier CRC: {identifier_crc:#010x}"


@cli.command(name="get-cache-entry")
@click.argument("address_hex")
@with_session
def get_cache_entry(session: "Session", address_hex: str) -> str:
    """Retrieve offline-cache metadata for an address.

    ADDRESS_HEX  hex-encoded address key.
    """
    address = bytes.fromhex(address_hex)
    found, label, data_mac = authdb.get_cache_entry(session, address=address)
    if not found:
        return "Not found."
    label_out = label if label else "(none)"
    mac_out = data_mac.hex() if data_mac else "(none)"
    return f"Found. Label: {label_out}. Data-MAC: {mac_out}"


@cli.command(name="get-all-cache")
@with_session
def get_all_cache(session: "Session") -> str:
    """Return all offline-cache entries stored on the device."""
    entries = authdb.get_all_cache(session)
    if not entries:
        return "Cache is empty."
    lines = ["address | label | data_mac"]
    for address, label, data_mac in entries:
        label_out = label if label else "(none)"
        mac_out = data_mac.hex() if data_mac else "(none)"
        lines.append(f"{address.hex()} | {label_out} | {mac_out}")
    return "\n".join(lines)


@cli.command(name="wipe-cache")
@with_session
def wipe_cache(session: "Session") -> str:
    """Wipe all offline-cache entries from the device."""
    authdb.wipe_cache(session)
    return "Cache wiped."


@cli.command(name="set-device-id")
@click.argument("device_id_hex")
@with_session
def set_device_id(session: "Session", device_id_hex: str) -> str:
    """Override the device_id on the device. DEBUG BUILDS ONLY.

    DEVICE_ID_HEX  32-byte device identifier (hex, 64 chars).
    """
    device_id = bytes.fromhex(device_id_hex)
    echoed = authdb.set_device_id(session, device_id=device_id)
    return f"device_id set to: {echoed.hex()}"


# ---------------------------------------------------------------------------
# Offline synchronization
# ---------------------------------------------------------------------------


@cli.command(name="queue-offline-operation")
@click.argument("address_hex")
@click.argument("old_value_hex")
@click.argument("new_value_hex")
@with_session
def queue_offline_operation(
    session: "Session", address_hex: str, old_value_hex: str, new_value_hex: str
) -> str:
    """Sign and append an offline operation to the on-device queue.

    Use when the host database is unreachable.

    ADDRESS_HEX    hex-encoded address.
    OLD_VALUE_HEX  hex-encoded current value; "" if the address is absent (INSERT).
    NEW_VALUE_HEX  hex-encoded new value; "" to delete.
    """
    address = bytes.fromhex(address_hex)
    old_value = bytes.fromhex(old_value_hex) if old_value_hex else b""
    new_value = bytes.fromhex(new_value_hex) if new_value_hex else b""
    sequence, mac, wallet_id = authdb.queue_offline_operation(
        session, address=address, old_value=old_value, new_value=new_value
    )
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    return f"Queued. Sequence: {sequence}. MAC: {mac.hex()}. Wallet ID: {id_hex}"


@cli.command(name="get-offline-operations")
@with_session
def get_offline_operations_cmd(session: "Session") -> str:
    """Return the current root/counter plus every queued offline operation."""
    current_root, counter, wallet_id, operations = authdb.get_offline_operations(session)
    root_hex = current_root.hex() if current_root else "(empty)"
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    lines = [
        f"Wallet ID: {id_hex}. Current root: {root_hex}. Counter: {counter}.",
        "sequence | address | old_value | new_value | mac",
    ]
    for op in operations:
        lines.append(
            f"{op.sequence} | {op.address.hex()} | "
            f"{op.old_value.hex() if op.old_value else ''} | "
            f"{op.new_value.hex() if op.new_value else ''} | {op.mac.hex()}"
        )
    return "\n".join(lines)


@cli.command(name="apply-offline-operations")
@click.option(
    "--file",
    "file_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="JSON file: a list of rebased operations, each with hex-encoded "
    "sequence/address/old_value/new_value/mac/proof/witness_address/witness_value "
    "(proof is a list of hex strings; old_value/new_value/witness_* may be omitted).",
)
@with_session
def apply_offline_operations_cmd(session: "Session", file_path: str) -> str:
    """Apply a batch of host-rebased offline operations from a JSON file."""
    import json

    with open(file_path) as f:
        raw_ops = json.load(f)

    operations = [
        authdb.RebasedOperation(
            sequence=op["sequence"],
            address=bytes.fromhex(op["address"]),
            old_value=bytes.fromhex(op["old_value"]) if op.get("old_value") else b"",
            new_value=bytes.fromhex(op["new_value"]) if op.get("new_value") else b"",
            mac=bytes.fromhex(op["mac"]),
            proof=[bytes.fromhex(h) for h in op.get("proof", [])],
            witness_address=bytes.fromhex(op["witness_address"]) if op.get("witness_address") else None,
            witness_value=bytes.fromhex(op["witness_value"]) if op.get("witness_value") else None,
        )
        for op in raw_ops
    ]

    applied_count, new_root, counter, last_applied_sequence, wallet_id, root_mac = (
        authdb.apply_offline_operations(session, operations)
    )
    root_hex = new_root.hex() if new_root else "(empty)"
    id_hex = wallet_id.hex() if wallet_id else "(none)"
    mac_hex = root_mac.hex() if root_mac else "(none)"
    return (
        f"Applied: {applied_count}/{len(operations)}. New root: {root_hex}. "
        f"Counter: {counter}. Last applied sequence: {last_applied_sequence}. "
        f"Wallet ID: {id_hex}. Root-attestation MAC: {mac_hex}"
    )


@cli.command(name="delete-offline-operations")
@with_session
def delete_offline_operations_cmd(session: "Session") -> str:
    """Garbage-collect queued operations up to the device's own last_applied_sequence."""
    deleted, remaining = authdb.delete_offline_operations(session)
    return f"Deleted: {deleted}. Remaining: {remaining}."


@cli.command(name="fast-forward-root")
@click.argument("new_root_hex")
@click.argument("counter", type=int)
@click.argument("wallet_id_hex")
@click.argument("mac_hex")
@with_session
def fast_forward_root(
    session: "Session", new_root_hex: str, counter: int, wallet_id_hex: str, mac_hex: str
) -> str:
    """Fast-forward this wallet's root to a state some device already attested to.

    MAC_HEX must be a root-attestation token previously returned as the
    `mac`/root_mac field from update-leaf or apply-offline-operations (on
    this device or on any other physical device sharing this wallet).

    NEW_ROOT_HEX  hex-encoded target root (32 bytes).
    COUNTER       target counter value; must be greater than the wallet's current counter.
    WALLET_ID_HEX hex-encoded wallet_id the attestation was issued for.
    MAC_HEX       hex-encoded root-attestation token.
    """
    new_root = bytes.fromhex(new_root_hex)
    wallet_id = bytes.fromhex(wallet_id_hex)
    mac = bytes.fromhex(mac_hex)
    new_counter, echoed_root, echoed_wallet_id = authdb.fast_forward_root(
        session, new_root=new_root, counter=counter, wallet_id=wallet_id, mac=mac
    )
    root_hex = echoed_root.hex() if echoed_root else "(none)"
    id_hex = echoed_wallet_id.hex() if echoed_wallet_id else "(none)"
    return f"Fast-forwarded. Counter: {new_counter}. Root: {root_hex}. Wallet ID: {id_hex}"
