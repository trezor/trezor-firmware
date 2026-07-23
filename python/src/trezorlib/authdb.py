from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Protocol, Tuple

from . import messages, ward
from .authdb_tree import AuthDbTree

if TYPE_CHECKING:
    from .transport.session import Session


ZERO_MAC = b"\x00" * 32


# The former AuthDb wire wrappers (init / set_root / lookup / update_leaf) were
# removed. The device interface is now the WARD flow in trezorlib.ward:
#   bootstrap: ward.init_sync -> ward.ingest_attestation -> ward.merge_state
#              (helper: ward.bootstrap)
#   write:     ward.set_entry -> ward.commit -> ward.finalize (helper: ward.write)
#   lookup:    ward.lookup
#   dev seed:  ward.debug_set_root


# ---------------------------------------------------------------------------
# dbinsert — WM-attested, Evolu-backed insert with a host offline queue
# ---------------------------------------------------------------------------


class QuotaManager(Protocol):
    """The WARD Manager (freshness authority), external to the device.

    sign_attestation(wallet_id, nonce, counter, mac) returns the WM's Ed25519
    signature over b"WARD ATTEST v1"||version||nonce||wallet_id||counter||mac --
    the freshness attestation WARDIngestAttestation verifies (bootstrap/refresh).

    sign_final(wallet_id, counter, mac) returns the WM's Ed25519 signature over
    b"WARD FINAL v1"||wallet_id||counter||mac -- the final attestation
    WARDConfirmCommit verifies before the device advances its counter.
    """

    def sign_attestation(
        self, wallet_id: bytes, nonce: bytes, counter: int, mac: bytes
    ) -> bytes: ...

    def sign_final(self, wallet_id: bytes, counter: int, mac: bytes) -> bytes: ...


class EvoluStore(Protocol):
    """The untrusted host store holding the attested root blob (Evolu's role)."""

    def get_root(self) -> Tuple[Optional[bytes], int, Optional[bytes]]:
        """Return (root, counter, root_mac); root/root_mac None for a fresh wallet."""
        ...

    def put_root(self, root: bytes, counter: int, root_mac: bytes) -> None:
        """Persist a freshly attested (root, counter, root_mac)."""
        ...


def dbinsert(
    session: "Session",
    qm: QuotaManager,
    evolu: EvoluStore,
    tree: AuthDbTree,
    queue: List[Tuple[bytes, bytes]],
    address: bytes,
    value: bytes,
    online: bool = True,
) -> int:
    """Insert (address, value), draining the host offline queue while online.

    Mirrors the reference algorithm on the WARD flow:

        root, counter_e, root_mac <- Evolu
        # ward.bootstrap does the authoritative on-device verification:
        #   init_sync (nonce) -> ingest_attestation (verify WM sig + counter floor)
        #   -> merge_state (assert mac binds root, install (root, counter_e)).
        insertToOfflineQueue(address, value)          # push last
        while online:
            re-bootstrap to Evolu's current attested root
            (addr, val) <- first queued
            ward.write  # set_entry -> commit_candidate -> confirm_commit
            upload_root                                # -> Evolu
            ward.lookup(addr) ; verify the leaf is a member at its new stamp
            on success -> deleteFromOfflineQueue (drop first)

    `tree` is the host's mirror of the Merkle tree, used to build proofs and
    kept in sync (leaves stamped with the global counter). `queue` is the
    caller-owned offline queue, mutated in place so pending items from earlier
    calls drain here too.

    Returns the number of queued entries applied this call.
    """
    # --- queue the change (push last) ---
    queue.append((address, value))

    # --- drain while online ---
    applied = 0
    while online and queue:
        cur_root, cur_counter, cur_root_mac = evolu.get_root()
        # Bootstrap/refresh the device to Evolu's currently-attested state:
        # ward.bootstrap verifies the WM freshness attestation on-device and adopts
        # the root (mac binds root to counter). Empty wallet -> counter 0, no root.
        ward.bootstrap(
            session,
            cur_counter if cur_root is not None else 0,
            cur_root_mac,
            cur_root,
            sign_attestation=qm.sign_attestation,
        )

        addr, val = queue[0]

        # build the proof of the OLD state; the new leaf is stamped with the new
        # GLOBAL counter (current root counter + 1).
        new_global = (cur_counter + 1) if cur_root is not None else 1
        old_counter = tree.get_counter(addr)
        if old_counter:  # UPDATE
            old_value = tree.get_value(addr)
            proof = tree.get_proof(addr)
            witness_address = witness_value = None
            witness_counter = None
        else:  # INSERT (or INIT on an empty tree)
            old_value = b""
            proof, witness_address, witness_counter, witness_value = (
                tree.get_nonmembership_proof(addr)
            )

        # WARD write round: set_entry -> commit -> WM sign candidate -> finalize.
        # The counter only advances on-device at finalize, after qm.sign_final.
        counter, new_root, _wid, mac = ward.write(
            session,
            addr,
            old_value,
            val,
            new_global,
            proof,
            old_counter=old_counter or None,
            witness_address=witness_address,
            witness_value=witness_value,
            witness_counter=witness_counter,
            sign_final=qm.sign_final,
        )
        # keep the host mirror in sync, stamping the leaf with the global counter
        tree.insert(addr, val, counter=new_global)

        # upload_root: persist the freshly attested state to Evolu
        if new_root is not None and mac is not None:
            evolu.put_root(new_root, counter, mac)

        # confirm the entry is now a member at its new global stamp
        valid, membership, _root_counter, _wid = ward.lookup(
            session, addr, val, tree.get_proof(addr), counter=new_global
        )
        if not (valid and membership):
            raise ValueError("post-insert lookup verification failed")

        # on success: drop the first entry and advance
        queue.pop(0)
        applied += 1

    return applied
