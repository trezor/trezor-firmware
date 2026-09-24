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

    AND IT ENROLS THE WALLET. A compare-and-swap needs something to compare against, and a WM
    that has never seen this wallet has nothing. So the ack carries the device's head and an
    authorisation for it: `head_init_sig`, Ed25519 under K_sig over the self-transition
    `(counter, root) -> (counter, root)` under its own tag, which can therefore never be replayed
    as an advance. Without it a wallet's opening head is whatever the first speaker claims, which
    is the same denial of service `wm_sig` closes for ordinary writes.

    ENROLMENT IS GENESIS ONLY, and this is the limit worth stating plainly because the fields
    look general enough to do more. A `head_init_sig` proves the head it names was a GENUINE
    STATE OF THIS WALLET. It does NOT prove that head is the LATEST one, and nothing a single
    device holds could: two devices at counter 40 and counter 57 both hold authentic signatures
    over their own heads. So a WM that accepted enrolment at an arbitrary counter would let
    whoever reached it first pin the head there, and the other device would be refused from then
    on against a state older than the wallet's real one -- a cross-device rollback, granted
    automatically. At counter 0 there is nothing to choose between, which is why enrolment is
    safe exactly there. `adopt.verify_round_attestation` enforces the matching rule from the
    other side: only counter 0 may attest itself.

    GAP(ward): A WM THAT LOST ITS REGISTER IS NOT COVERED BY THIS and must not be. Recovering one
    means restoring its persisted head, or a named recovery mechanism with an operator policy
    deciding which device's claim wins. Overloading enrolment with it would make the rollback
    above the supported path rather than an attack.

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
