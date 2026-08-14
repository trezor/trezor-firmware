from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardSync, WardSyncAck


async def sync(msg: WardSync) -> WardSyncAck:
    """Begin a sync round: mint the nonce the WM's attestation must be bound to.

    Minting happens BEFORE the host talks to the WM, and that ordering is the point. The
    WM has to sign a value it could not have known in advance, so a host cannot keep a
    drawer of previously-signed anchors and serve whichever suits it. Against a host-only
    adversary -- the likelier one, since compromising the WM is a separate and harder
    event -- that closes replay entirely.

    The ack also states the device's current counter, which makes this the "where are we"
    exchange as well as the round opener. A host that lost a write's response cannot
    otherwise tell a completed write from one that never happened: it retries, serves a proof
    against a root the device has already moved past, and is refused with nothing to say why.
    """
    from trezor.crypto import random
    from trezor.messages import WardSyncAck

    from . import round as sync_round
    from .attest import NONCE_LENGTH
    from .common import require_initialized
    from .keys import derive_ward_id
    from .root import get_counter

    require_initialized()

    nonce = random.bytes(NONCE_LENGTH)
    sync_round.begin(nonce)

    return WardSyncAck(
        nonce=nonce, ward_id=await derive_ward_id(), counter=await get_counter()
    )
