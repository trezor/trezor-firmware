from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def set_root(
    session: "Session",
    root: bytes,
    mac: Optional[bytes] = None,
    device_id: Optional[bytes] = None,
) -> tuple[int, Optional[bytes]]:
    """Store a new Merkle root on the device. DEBUG BUILDS ONLY.

    Returns (counter, identifier).
    """
    resp = session.call(
        messages.AuthDbSetRoot(root=root, mac=mac, device_id=device_id),
        expect=messages.AuthDbSetRootResponse,
    )
    return resp.counter, resp.identifier


def lookup(
    session: "Session",
    address: bytes,
    value: Optional[bytes],
    proof: list[bytes],
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
) -> tuple[bool, bool, int, Optional[bytes]]:
    """Verify an MPT proof against the stored root.

    For a membership proof supply value; leave witness_address/witness_value None.
    For a non-membership proof supply witness_address and witness_value; value may be None.

    Returns (valid, membership, counter, identifier).
    """
    resp = session.call(
        messages.AuthDbLookup(
            address=address,
            value=value,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
        ),
        expect=messages.AuthDbLookupResponse,
    )
    membership = resp.membership if resp.membership is not None else True
    return resp.valid, membership, resp.counter, resp.identifier


def clear_root(session: "Session") -> Optional[bytes]:
    """Wipe the stored Merkle root. DEBUG BUILDS ONLY.

    Returns identifier.
    """
    resp = session.call(
        messages.AuthDbClearRoot(),
        expect=messages.AuthDbClearRootResponse,
    )
    return resp.identifier


def update_leaf(
    session: "Session",
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    proof: list[bytes],
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
    mac: Optional[bytes] = None,
    device_id: Optional[bytes] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Atomically update a leaf in the Merkle tree.

    old_value=b"" means the address is currently absent (INSERT / INIT).
    new_value=b"" means delete the address (DELETE).
    mac + device_id skip the on-screen confirmation if they match a prior approve() call.

    Returns (counter, new_root, identifier, mac, auth_mac).
    new_root/mac are None if tree is now empty.
    auth_mac is set in debug/auto-approve mode: HMAC(device_key, old_leafHash||new_leafHash).
    """
    resp = session.call(
        messages.AuthDbUpdateLeaf(
            address=address,
            old_value=old_value,
            new_value=new_value,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
            mac=mac,
            device_id=device_id,
        ),
        expect=messages.AuthDbUpdateLeafResponse,
    )
    return resp.counter, resp.new_root, resp.identifier, resp.mac, resp.auth_mac


def set_cache_entry(
    session: "Session",
    address: bytes,
    label: Optional[str] = None,
    data_mac: Optional[bytes] = None,
) -> int:
    """Store label and/or data_mac for address in the device offline cache.

    Returns identifier_crc (low 4 bytes of device_id) for sanity-checking.
    """
    resp = session.call(
        messages.AuthDbSetCacheEntry(address=address, label=label, data_mac=data_mac),
        expect=messages.AuthDbSetCacheEntryResponse,
    )
    return resp.identifier_crc


def get_cache_entry(
    session: "Session",
    address: bytes,
) -> tuple[bool, Optional[str], Optional[bytes]]:
    """Retrieve cached metadata for address.

    Returns (found, label, data_mac).
    """
    resp = session.call(
        messages.AuthDbGetCacheEntry(address=address),
        expect=messages.AuthDbGetCacheEntryResponse,
    )
    return resp.found, resp.label, resp.data_mac


def get_all_cache(
    session: "Session",
) -> list[tuple[bytes, Optional[str], Optional[bytes]]]:
    """Return all cached entries as (address, label, data_mac) tuples."""
    resp = session.call(
        messages.AuthDbGetAllCache(),
        expect=messages.AuthDbGetAllCacheResponse,
    )
    return [(e.address, e.label, e.data_mac) for e in resp.entries]


def wipe_cache(session: "Session") -> None:
    """Wipe all offline-cache entries from the device."""
    session.call(messages.AuthDbWipeCache(), expect=messages.AuthDbWipeCacheResponse)


def set_device_id(
    session: "Session",
    device_id: bytes,
) -> bytes:
    """Override the device_id on the device. DEBUG BUILDS ONLY.

    Returns the echoed device_id.
    """
    resp = session.call(
        messages.AuthDbSetDeviceId(device_id=device_id),
        expect=messages.AuthDbSetDeviceIdResponse,
    )
    return resp.device_id


def approve(
    session: "Session",
    address: bytes,
    value: bytes,
) -> tuple[bytes, Optional[bytes]]:
    """Pre-authorize an (address, value) pair on the device.

    The user confirms on-screen; the device returns a MAC token that can be
    passed to future update_leaf calls to skip the confirmation dialog.

    Returns (mac, identifier).
    """
    resp = session.call(
        messages.AuthDbApprove(address=address, value=value),
        expect=messages.AuthDbApproveResponse,
    )
    return resp.mac, resp.identifier
