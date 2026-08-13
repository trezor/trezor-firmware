from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDSync, WARDSyncAck


async def sync(msg: WARDSync) -> WARDSyncAck:
    """Begin a sync round: mint the nonce the WM's attestation must be bound to.

    Minting happens BEFORE the host talks to the WM, and that ordering is the point. The
    WM has to sign a value it could not have known in advance, so a host cannot keep a
    drawer of previously-signed anchors and serve whichever suits it. Against a host-only
    adversary -- the likelier one, since compromising the WM is a separate and harder
    event -- that closes replay entirely.
    """
    from trezor.crypto import random
    from trezor.messages import WARDSyncAck

    from . import round as sync_round
    from .attest import NONCE_LENGTH
    from .common import require_initialized
    from .keys import derive_ward_id

    require_initialized()

    nonce = random.bytes(NONCE_LENGTH)
    sync_round.begin(nonce)

    return WARDSyncAck(nonce=nonce, ward_id=await derive_ward_id())
