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

    AND IT SEEDS THE WM. A compare-and-swap needs something to compare against, and a WM that has
    never seen this wallet -- or whose register was lost -- has nothing. So the ack carries the
    device's head and an authorisation for it: `head_init_sig`, Ed25519 under K_sig over the
    self-transition `(counter, root) -> (counter, root)` under its own tag, which can therefore
    never be replayed as an advance. Without it a wallet's opening head is whatever the first
    speaker claims, which is the same denial of service `wm_sig` closes for ordinary writes.

    SENT ALWAYS, not only when the device believes the WM is new. The device cannot know the WM's
    state -- that is the WM's business -- and guessing "it already knows us" strands a genesis
    wallet with no way to open its history. The WM ignores it once it holds a head, so the cost
    is one signature per round. The service channel has always worked this way; this brings
    connect level with it.
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

    return WardSyncAck(
        nonce=nonce,
        ward_id=ward_id,
        counter=counter,
        root=root,
        head_init_sig=head_init_sig(await derive_k_sig(), ward_id, counter, root),
    )
