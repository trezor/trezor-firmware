from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardSync, WardSyncAck


async def sync(msg: WardSync) -> WardSyncAck:
    """Begin a sync round: mint the nonce the WM's attestation must be bound to.

    Minted before the host talks to the WM, so the WM must sign a value it could not know in
    advance and a host cannot replay stored attestations. The ack also reports the device's
    counter, so a host that lost a write's response can tell whether it landed.

    At counter 0 only, the ack also enrols the wallet with `head_init_sig` over the genesis
    self-transition. Above genesis it is never issued: it proves a head was genuine, not latest,
    so an enrolment at an arbitrary counter would let the first device to reach an empty WM pin an
    older head -- a cross-device rollback.
    """
    from trezor.crypto import random
    from trezor.messages import WardSyncAck

    from . import round as sync_round
    from .attest import NONCE_LENGTH
    from .cas import head_init_sig
    from .common import require_initialized
    from .keys import derive_k_sig, derive_ward_id
    from .root import get_counter, get_root

    require_initialized()

    nonce = random.bytes(NONCE_LENGTH)
    sync_round.begin(nonce)

    ward_id = await derive_ward_id()
    counter = await get_counter()
    root = await get_root()

    init = None
    if counter == 0:
        init = head_init_sig(await derive_k_sig(), ward_id, counter, root)

    return WardSyncAck(
        nonce=nonce,
        ward_id=ward_id,
        counter=counter,
        root=root if counter == 0 else None,
        head_init_sig=init,
    )
