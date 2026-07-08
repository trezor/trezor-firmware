from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Protocol, Tuple

from . import messages
from .authdb_tree import AuthDbTree

if TYPE_CHECKING:
    from .transport.session import Session


ZERO_MAC = b"\x00" * 32


# ---------------------------------------------------------------------------
# Wire wrappers — one per device interface (init / set_root / lookup / update_leaf)
# ---------------------------------------------------------------------------


def init(
    session: "Session",
    qm_counter: int,
    qm_signature: bytes,
    root: Optional[bytes] = None,
    counter: Optional[int] = None,
    root_mac: Optional[bytes] = None,
) -> tuple[int, Optional[bytes], Optional[int], Optional[bytes], Optional[bytes]]:
    """Bootstrap the device's trusted AuthDB state from untrusted host storage.

    The device verifies the Quota-Manager Ed25519 signature over
    b"AUTHDB QM v1" || wallet_id || qm_counter(4B BE) against its provisioned
    QM public key and stores qm_counter as the qm_last_counter anti-rollback
    ceiling. If `root` is supplied (from Evolu), the device also verifies
    counter == qm_counter and root_mac == HMAC(root_mac_key, wallet_id ||
    counter || root) before installing it; a fresh wallet supplies no root.

    Returns (qm_last_counter, wallet_id, counter, root, root_mac).
    """
    resp = session.call(
        messages.AuthDbInit(
            qm_counter=qm_counter,
            qm_signature=qm_signature,
            root=root,
            counter=counter,
            root_mac=root_mac,
        ),
        expect=messages.AuthDbInitResponse,
    )
    return (
        resp.qm_last_counter,
        resp.wallet_id,
        resp.counter,
        resp.root,
        resp.root_mac,
    )


def set_root(
    session: "Session",
    root: bytes,
    mac: Optional[bytes] = None,
    wallet_id: Optional[bytes] = None,
    counter: Optional[int] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Install a (root, counter) state attested by a device-produced MAC.

    mac defaults to the all-zero sentinel -- a plain unauthenticated root
    injection, accepted ONLY on debug builds. Supply a real mac (from
    update_leaf()'s `mac`) plus wallet_id and the attested counter to use the
    production-safe path: the device checks wallet_id == its own wallet_id,
    counter strictly greater than the stored counter (anti-rollback), and
    mac == HMAC(root_mac_key, wallet_id || counter || root).

    Returns (counter, wallet_id, new_root, root_mac).
    """
    resp = session.call(
        messages.AuthDbSetRoot(
            root=root,
            mac=mac if mac is not None else ZERO_MAC,
            wallet_id=wallet_id,
            counter=counter,
        ),
        expect=messages.AuthDbSetRootResponse,
    )
    return resp.counter, resp.wallet_id, resp.new_root, resp.root_mac


def lookup(
    session: "Session",
    address: bytes,
    value: Optional[bytes],
    proof: list[bytes],
    counter: Optional[int] = None,
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
    witness_counter: Optional[int] = None,
) -> tuple[bool, bool, int, Optional[bytes]]:
    """Verify an MPT proof against the stored root.

    For a membership proof supply value + counter (address's leaf counter);
    leave witness_* None. For a non-membership proof supply witness_address,
    witness_counter, and witness_value; value/counter may be None.

    Returns (valid, membership, counter, wallet_id). The response `counter`
    is the ROOT-level (global) counter, not the leaf counter passed in.
    """
    resp = session.call(
        messages.AuthDbLookup(
            address=address,
            value=value,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
            counter=counter,
            witness_counter=witness_counter,
        ),
        expect=messages.AuthDbLookupResponse,
    )
    membership = resp.membership if resp.membership is not None else True
    return resp.valid, membership, resp.counter, resp.wallet_id


def update_leaf(
    session: "Session",
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    new_counter: int,
    proof: list[bytes],
    old_counter: Optional[int] = None,
    witness_address: Optional[bytes] = None,
    witness_value: Optional[bytes] = None,
    witness_counter: Optional[int] = None,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Atomically update a leaf in the Merkle tree.

    old_value=b"" means the address is currently absent (INSERT / INIT).
    new_value=b"" means delete the address (DELETE).

    Global-counter model: new_counter must equal the current root counter + 1
    -- the device stamps the changed leaf with that new global counter and
    rejects any other value. old_counter is the leaf's previous global stamp.

    Returns (counter, new_root, wallet_id, mac). new_root/mac are None if the
    tree is now empty.
    """
    resp = session.call(
        messages.AuthDbUpdateLeaf(
            address=address,
            old_value=old_value,
            new_value=new_value,
            new_counter=new_counter,
            old_counter=old_counter,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
            witness_counter=witness_counter,
        ),
        expect=messages.AuthDbUpdateLeafResponse,
    )
    return resp.counter, resp.new_root, resp.wallet_id, resp.mac


# ---------------------------------------------------------------------------
# dbinsert — QM-attested, Evolu-backed insert with a host offline queue
# ---------------------------------------------------------------------------


class QuotaManager(Protocol):
    """The authoritative per-wallet global counter, external to the device.

    get_signed_counter() returns (counter, signature) where signature is the
    QM's Ed25519 signature over b"AUTHDB QM v1" || wallet_id || counter(4B BE)
    -- exactly what AuthDbInit verifies on-device against the provisioned QM
    public key.
    """

    def get_signed_counter(self) -> Tuple[int, bytes]: ...


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

    Mirrors the reference algorithm:

        last_counter_qm            <- Quota Manager
        root, counter_e, root_mac  <- Evolu
        # AuthDbInit does the authoritative verification on-device:
        #   verify QM Ed25519 signature, verify counter_e == last_counter_qm,
        #   verify root_mac over (root, counter_e), then install the root.
        insertToOfflineQueue(address, value)          # push last
        while online:
            set_root                                   # (re)install attested root
            (addr, val) <- first queued
            dbchange                                   # update_leaf, global stamp
            upload_root                                # -> Evolu
            latest_counter_qm <- Quota Manager
            verify latest_counter_qm == last_counter_qm + 1
            dblookup(addr) ; verify the leaf is a member at its new stamp
            on success -> deleteFromOfflineQueue (drop first)

    `tree` is the host's mirror of the Merkle tree, used to build proofs and
    kept in sync (leaves stamped with the global counter). `queue` is the
    caller-owned offline queue, mutated in place so pending items from earlier
    calls drain here too.

    Returns the number of queued entries applied this call.
    """
    # --- bootstrap: AuthDbInit does the authoritative QM-sig / counter / MAC checks ---
    last_counter_qm, qm_sig = qm.get_signed_counter()
    root, counter_e, root_mac = evolu.get_root()
    if root is not None and last_counter_qm != counter_e:
        # cheap host-side early-out; the device re-checks this in init()
        raise ValueError("QM counter != Evolu counter")

    _qm_last, wallet_id, _counter, _root, _root_mac = init(
        session,
        qm_counter=last_counter_qm,
        qm_signature=qm_sig,
        root=root,
        counter=counter_e if root is not None else None,
        root_mac=root_mac if root is not None else None,
    )

    # --- queue the change (push last) ---
    queue.append((address, value))

    # --- drain while online ---
    applied = 0
    while online and queue:
        cur_root, cur_counter, cur_root_mac = evolu.get_root()
        # (re)install the currently attested root on the device before changing it
        if cur_root is not None and cur_root_mac is not None:
            set_root(
                session,
                cur_root,
                mac=cur_root_mac,
                wallet_id=wallet_id,
                counter=cur_counter,
            )

        addr, val = queue[0]

        # dbchange: build the proof of the OLD state and update the leaf. The new
        # leaf is stamped with the new GLOBAL counter (current root counter + 1).
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

        counter, new_root, _wid, mac = update_leaf(
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
        )
        # keep the host mirror in sync, stamping the leaf with the global counter
        tree.insert(addr, val, counter=new_global)

        # upload_root: persist the freshly attested state to Evolu
        if new_root is not None and mac is not None:
            evolu.put_root(new_root, counter, mac)

        # verify the QM advanced by exactly one (the Ed25519 signature itself is
        # verified authoritatively on-device by the next AuthDbInit).
        latest_counter_qm, _latest_sig = qm.get_signed_counter()
        if latest_counter_qm != last_counter_qm + 1:
            raise ValueError("QM counter did not advance by exactly 1")

        # dblookup: confirm the entry is now a member at its new global stamp
        # (== latest_counter_qm == last_counter_qm + 1).
        valid, membership, _root_counter, _wid = lookup(
            session, addr, val, tree.get_proof(addr), counter=new_global
        )
        if not (valid and membership):
            raise ValueError("post-insert lookup verification failed")

        # on success: drop the first entry and advance
        queue.pop(0)
        applied += 1
        last_counter_qm = latest_counter_qm

    return applied
