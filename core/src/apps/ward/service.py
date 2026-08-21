"""The WARD service channel: a daemon that owns the replica, on an interface of its own.

WHY A SECOND CHANNEL EXISTS AT ALL. A WARD read goes through `context.call()`, which reaches
CURRENT_CONTEXT -- the workflow currently executing. On a connect build that makes WARD's store
structurally Suite's store, and a read can only happen while Suite is answering. A daemon on its
own interface can be asked at any point in any workflow, and can be asked by the device rather
than only answer it.

THE INVERSION. `WardServiceOpen` is the LAST host-initiated application message on this channel.
Afterwards the device is the sole initiator: it writes a request and reads the reply. One message
stream with no request ids cannot carry two independent conversations -- a reply and an unrelated
request are indistinguishable -- so rather than add ids, the direction is fixed.

WHAT BINDING IS AND IS NOT. It establishes WHICH daemon this device talks to, and nothing else.
It does not make the service usable: readiness comes from a sync, which happens when a WARD
operation first needs it. And it does not choose a transport -- that is decided at build time.
"""

from micropython import const
from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from trezor import protobuf
    from trezor.messages import WardEntryAck, WardServiceOpen, WardServiceOpenAck
    from trezor.protobuf import MessageType as LoadedMessageType
    from trezor.wire.protocol_common import Message
    from trezor.wire.thp.channel import Channel


# HOW LONG A REVERSE RPC MAY TAKE, END TO END. A daemon that stops answering must not hang the
# wallet workflow that is waiting on it: WARD reads fail closed, and a hang is the one failure mode
# that does not. Generous, because the daemon may have to consult a database and build a proof.
#
# IT COVERS THE WRITE AS WELL AS THE READ, and that is not a detail. `Channel.write` waits for the
# THP ack, and a daemon that has gone away acks nothing -- so the retransmission machinery is what
# ends that wait, after MAX_RETRANSMISSION_COUNT attempts and upwards of a hundred seconds. Timing
# only the read leaves the failure this bound exists to prevent exactly where it was: the workflow
# parks in the write, and the deadline below is never reached.
RPC_TIMEOUT_MS = const(30_000)

# The service protocol this firmware speaks. Bumped when the message set changes shape, so a
# daemon built against an older firmware is refused by name instead of misreading a field.
PROTOCOL_VERSION = 1

_IFACE_NUM_OFF = const(0)
_CHANNEL_ID_OFF = const(1)
_SESSION_ID_OFF = const(3)
_BINDING_LEN = const(4)


def get_binding() -> tuple[int, int, int] | None:
    """(iface_num, channel_id, session_id) of the bound service, or None.

    Every field is needed. The channel id alone does not identify a channel: ids are reallocated,
    and a reallocation on ANOTHER interface would otherwise be indistinguishable from the service
    still being there.
    """
    from storage.cache import get_sessionless_cache
    from storage.cache_common import APP_WARD_SERVICE

    raw = get_sessionless_cache().get(APP_WARD_SERVICE)
    if raw is None:
        return None
    return (
        raw[_IFACE_NUM_OFF],
        int.from_bytes(raw[_CHANNEL_ID_OFF:_SESSION_ID_OFF], "big"),
        raw[_SESSION_ID_OFF],
    )


def set_binding(iface_num: int, channel_id: int, session_id: int) -> None:
    from storage.cache import get_sessionless_cache
    from storage.cache_common import APP_WARD_SERVICE

    get_sessionless_cache().set(
        APP_WARD_SERVICE,
        bytes([iface_num]) + channel_id.to_bytes(2, "big") + bytes([session_id]),
    )


def clear_binding() -> None:
    """Forget which channel is the service. Does NOT unpin the daemon's key.

    The two are different facts and are forgotten at different times: the channel goes away
    whenever the daemon restarts or the cable moves, while the daemon's identity is meant to
    survive exactly that.
    """
    from storage.cache import get_sessionless_cache
    from storage.cache_common import APP_WARD_SERVICE

    get_sessionless_cache().delete(APP_WARD_SERVICE)


async def service(msg: WardServiceOpen) -> WardServiceOpenAck:
    """Bind this channel as the WARD service.

    Deliberately does NOT require a pre-existing service session: an unknown session id arrives as
    an ephemeral seedless context, and this handler is what allocates the real slot. And it does
    not check which channel is currently dispatched, because this channel legitimately is -- that
    is how this message got here.
    """
    from storage import cache_thp
    from storage import ward as storage_ward
    from trezor import wire
    from trezor.messages import WardServiceOpenAck
    from trezor.wire import context

    if not utils.USE_WARD_SERVICE_CHANNEL:
        # Unreachable in a connect build, where the handler is not registered and this module is
        # not frozen in. Stated anyway so the refusal does not depend on registration alone.
        raise wire.DataError("this firmware does not serve WARD over a service channel")

    ctx = context.get_context()

    # THE INTERFACE IS THE AUTHORISATION BOUNDARY. Everything below trusts that this channel is
    # the daemon's, and the only reason to believe that is which interface it arrived on -- a
    # separate OS claim that Suite does not hold.
    if not wire.is_ward_interface(ctx.iface):
        raise wire.DataError("WARD service must be opened on the WARD interface")

    if msg.protocol_version != PROTOCOL_VERSION:
        raise wire.DataError("unsupported WARD service protocol version")

    channel = ctx.channel

    # ONE DAEMON, PINNED. Pairing proves only that the host holds a credential this device issued,
    # which every paired host does -- Suite included. Without this, any paired host could open the
    # WARD interface and answer for the replica.
    host_key = channel.get_host_static_public_key()
    pinned = storage_ward.get_service_host_key()
    if pinned is None:
        # PINNING IS A FLASH WRITE, so a first bind needs the device unlocked. Said explicitly
        # rather than left to fail inside `config.set`, which would surface as an opaque storage
        # error at the point where the daemon is least able to interpret it. Re-binding an
        # already-pinned daemon writes nothing and works while locked, which is the case that
        # matters at boot: the daemon comes up before the user does.
        from trezor import config

        if not config.is_unlocked():
            raise wire.DataError("unlock the device to bind the WARD service")
        storage_ward.set_service_host_key(host_key)
    elif pinned != host_key:
        # Not repairable by connecting a different daemon: the pin is in flash precisely so that
        # unplugging the device does not clear it. Recovering from a lost daemon key is an
        # ownership migration, with a user decision in it, and belongs in its own path.
        raise wire.DataError("another daemon is bound as the WARD service")

    # NEVER DISPLACE A LIVE SERVICE. The displaced binding is what some in-flight operation is
    # holding, so replacing it would strand that operation on a channel nothing answers for.
    #
    # LIVE, not merely recorded. A daemon restart leaves a binding naming a channel that is gone,
    # and refusing on that would lock the service out until the device rebooted -- so a recorded
    # binding only counts while its channel is still open.
    #
    # NOT REACHABLE TODAY, and worth saying so rather than implying coverage. Two channels of one
    # daemon cannot coexist: THP replaces a channel arriving with an already-known host static
    # key, so the older one is closed. A channel with a different key fails the pin above. And a
    # repeat open on the bound channel itself is never dispatched, because binding hands the
    # channel to the device. Kept because all three of those are properties of other code, and a
    # binding must not be displaced silently if any of them changes.
    bound = get_binding()
    if bound is not None:
        from trezorthp import channel_is_open

        if channel_is_open(bound[1]):
            raise wire.DataError("a WARD service is already bound")

    cache_thp.create_ward_service_session(
        channel_id=channel.channel_id_bytes(),
        session_id=ctx.session_id.to_bytes(1, "big"),
    )
    set_binding(ctx.iface.iface_num(), ctx.channel_id, ctx.session_id)

    # THE CONVERSATION INVERTS HERE. From now on the device asks and the daemon answers, so the
    # interface's dispatcher must stop reading this channel -- otherwise it and the workflow
    # awaiting its own reply would race for the same incoming message.
    channel.iface_ctx.release_dispatch()

    return WardServiceOpenAck()


# --- talking to the service ---------------------------------------------------------------
#
# THE DEVICE ASKS AND THE DAEMON ANSWERS, and after binding that is the only direction. One
# message stream with no request ids cannot carry two independent conversations: a reply and an
# unrelated request are indistinguishable. Rather than add ids, the channel is inverted.
#
# WHAT ENFORCES IT IS STRUCTURAL, not a flag. Once bound, the interface's dispatcher releases the
# channel (`InterfaceContext.release_dispatch`), so nothing is reading it except the workflow that
# just wrote a request. An earlier design gated the receive boundary on an "RPC in flight" flag;
# that would have had to be right about `expecting_message`, which `Channel.write` clears as its
# first act, and about ACK piggybacking, which can deliver a valid fast response while
# `expecting_ack` is still set. Having exactly one reader removes the question.
#
# An unsolicited message from the daemon therefore is not dispatched at all: it sits in the
# channel until the next RPC reads it, fails the type check below, and fails that operation. That
# is the fail-closed direction, and it costs the daemon its own conversation rather than the
# device's integrity.


def _service_channel() -> tuple[Channel, int]:
    """The bound channel, reattached so it can be written to, and the session id to write on.

    REATTACHING IS NOT OPTIONAL. The Rust channel outlives MicroPython session restarts but the
    `Channel` object does not, and a channel that is not its interface's `active_channel` cannot
    be written at all -- `Channel.write` pokes a write loop that drains only that one.
    """
    from trezor.wire import DataError, context

    bound = get_binding()
    if bound is None:
        raise DataError("no WARD service is bound")
    iface_num, channel_id, session_id = bound

    # Reached from the WALLET workflow, so the context here is Suite's channel -- borrowed only
    # for the `ThpContext` it hangs off, which is the one object that knows every interface.
    thp_ctx = context.get_context().channel.iface_ctx.thp_ctx
    return thp_ctx.attach_existing_channel(iface_num, channel_id), session_id


async def _rpc(
    request: protobuf.MessageType, *expected: type[LoadedMessageType]
) -> "protobuf.MessageType":
    """Ask the service one question and read its answer.

    The answer must be one of `expected` and must arrive on the service's own session. Anything
    else fails the operation rather than being interpreted: the daemon is the only party on this
    channel, so a surprise here means the conversation has desynchronised, and continuing would
    mean acting on a message meant for something else. It also costs the daemon its channel --
    see `_desynchronised` for why the operation alone is not enough.
    """
    from trezor import loop
    from trezor.wire.message_handler import wrap_protobuf_load

    channel, session_id = _service_channel()

    async def exchange() -> "tuple[int, Message]":
        # ONE DEADLINE OVER BOTH HALVES. Neither `write` nor `read` has one of its own, and the
        # wait that actually strands a silent daemon is the FIRST: `write` returns when the ack
        # arrives, so with nothing at the other end it sits there until THP exhausts its
        # retransmissions. Racing them as one coroutine bounds the pair.
        await channel.write(request, session_id)
        return await channel.read()

    # `loop.sleep` returns an int, the exchange a tuple -- which is how the race is decided.
    answer = await loop.race(exchange(), loop.sleep(RPC_TIMEOUT_MS))
    if not isinstance(answer, tuple):
        raise _desynchronised(channel, "the WARD service did not answer")

    reply_session_id, message = answer
    if reply_session_id != session_id:
        raise _desynchronised(channel, "WARD service answered on another session")

    for expected_type in expected:
        if message.type == expected_type.MESSAGE_WIRE_TYPE:
            return wrap_protobuf_load(message.data, expected_type)

    raise _desynchronised(channel, "unexpected message from the WARD service")


def _desynchronised(channel: Channel, what: str) -> Exception:
    """Tear the service channel down, and return the error to raise for having done so.

    WHY THE CHANNEL GOES RATHER THAN JUST THE OPERATION. Each of these means the device no longer
    knows where it is in the conversation: a request whose answer never came may still be answered
    later, and a reply that is not the one asked for leaves the next read one message behind
    forever. Since the device is the sole initiator, nothing else will ever resynchronise it --
    there is no host turn in which to notice. Closing the channel is the resynchronisation, and it
    costs the daemon a reconnect rather than costing the device its integrity.

    A TIMED-OUT WRITE ALSO HAS TO GO. The abandoned message is still pending in the THP channel,
    and the retransmission loop would keep re-sending it with no `send_buffer` behind it. Closing
    discards it.

    THE PIN IS NOT TOUCHED. This says the transport went away, which is what a daemon restart looks
    like; it says nothing about WHICH daemon is entitled to the role. Erasing the pin here would
    turn every dropped cable into an ownership migration.

    Returned rather than raised so the caller's `raise` is where the flow ends, which keeps the
    teardown from reading like a side effect of an unrelated error path.
    """
    from trezor.wire import DataError

    exc = DataError(what)
    clear_binding()
    channel.clear(exc)
    return exc


async def fetch(entry_key: bytes, retry: bool = True) -> "WardEntryAck":
    """Ask the service for its leaf at this path. Verifies NOTHING -- the caller does that.

    HEAD-AWARE, unlike the connect-mode request it replaces. The device says which head it holds,
    so the service can answer `WardSyncRequired` instead of serving a proof that cannot verify
    against it. Both fields are needed: several roots may share a counter across forks, so the
    counter alone does not name a head.

    `WardSyncRequired` needs no authentication. Lying about it only forces an authenticated sync,
    which is a denial of service rather than a way to corrupt anything -- and the sync it forces
    is the same one that would have happened anyway, so there is nothing to gain by it.
    """
    from trezor.messages import WardEntryAck, WardServiceFetch, WardSyncRequired
    from trezor.wire import DataError

    from .root import get_counter, get_root

    answer = await _rpc(
        WardServiceFetch(
            entry_key=entry_key,
            current_counter=await get_counter(),
            current_root=await get_root(),
        ),
        WardEntryAck,
        WardSyncRequired,
    )

    # COMPARED BY WIRE TYPE, not `isinstance`: message classes here are C-backed and are not
    # valid second arguments to `isinstance`, which fails at runtime rather than at import.
    if answer.MESSAGE_WIRE_TYPE == WardSyncRequired.MESSAGE_WIRE_TYPE:
        if retry:
            # ONE SYNC AND ONE RETRY, and then it is an error. A daemon that still says "out of
            # sync" about the head the device just adopted from that same daemon is disagreeing
            # with itself, and asking again cannot resolve it -- it can only spin in front of the
            # user. The read fails closed, which is the safe direction.
            await sync()
            return await fetch(entry_key, retry=False)
        raise DataError("WARD service reports this device is out of sync")

    return answer


# --- becoming ready -----------------------------------------------------------------------
#
# ONE RPC WHERE THE CONNECT PATH TAKES THREE. `WardSync` minted a nonce, `WardIngestAttestation`
# checked the WM's answer against it, and `WardVerifyChain` proved descent and adopted -- three
# separate host requests, which is exactly why the round's nonce had to live in the session cache
# (`round.py`). As one exchange the nonce is a local across a single `await`.
#
# THE CACHE ENTRY STAYS ANYWAY, and that is a deliberate trade. `verify_round_attestation`,
# `require_attested_round` and `adopt` all read the round from there, and they are the audited
# path: the nonce binding, the counter rules, and above all the settle-then-persist-then-latch
# order that recovery depends on. Reusing them costs one cache write per sync; forking them to
# take the nonce as an argument would cost a second copy of that order, which is the last thing
# in WARD that should exist twice.
#
# CHAIN-ONLY, which REMOVES a weaker path rather than adding one. The daemon owns the replica and
# its history, so it can always produce the links; there is no reason to accept a head on the WM's
# word plus a mac when descent from this device's own head is available. The two guarantees are
# complementary -- the chain gives descent, the attestation gives currency -- and they are joined
# by requiring the fold to end exactly at the attested counter with a root reproducing its mac.


async def sync() -> None:
    """Ask the service for the current head and adopt it, or raise.

    The nonce is minted HERE, before the daemon talks to the WM, and that ordering is the whole
    freshness argument: the WM must sign a value nobody could have known in advance, so a drawer
    of previously-signed anchors is useless.

    HEAD-INIT IS ALWAYS SENT, not only when the device thinks the WM is new. The device cannot
    know whether the WM has ever seen this wallet -- that is the WM's state, not the device's --
    and guessing wrong in the "it knows" direction would strand a genesis wallet with no way to
    open its history. The WM ignores it once it holds a head, so the cost is one signature.
    """
    from trezor.crypto import random
    from trezor.messages import WardSyncRequest, WardSyncResponse
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import (
        adopt,
        require_attested_round,
        verify_head_mac,
        verify_round_attestation,
    )
    from .attest import NONCE_LENGTH, root_mac
    from .cas import head_init_sig, verify_chain_step
    from .common import require_initialized
    from .keys import derive_k_auth, derive_k_mac, derive_k_sig, derive_ward_id
    from .root import get_counter, get_root

    require_initialized()

    ward_id = await derive_ward_id()
    counter = await get_counter()
    root = await get_root()

    # The mac of the head the device ALREADY holds -- the opening head a WM that has never seen
    # this wallet has nothing to compare against. It cannot compute one itself, holding no key of
    # ours, so it has to be supplied and authorised or a wallet's first head is whatever the first
    # speaker claims.
    current_mac = root_mac(await derive_k_mac(), ward_id, counter, root)

    nonce = random.bytes(NONCE_LENGTH)
    sync_round.begin(nonce)

    answer = await _rpc(
        WardSyncRequest(
            nonce=nonce,
            ward_id=ward_id,
            current_counter=counter,
            current_root=root,
            current_mac=current_mac,
            head_init_sig=head_init_sig(await derive_k_sig(), ward_id, current_mac),
        ),
        WardSyncResponse,
    )

    # Same verification as `ingest`, and deliberately the same code: the attestation must be
    # bound to THIS round's nonce, and nothing here adopts on the strength of it alone.
    attested_counter, attested_mac = await verify_round_attestation(answer)
    if attested_counter < counter:
        # Anti-rollback. A malicious WM cannot forge a mac, so its entire remaining freedom is to
        # replay a state this wallet genuinely reached; this is what bounds which ones. Equality
        # is fine -- re-reading the same head is a no-op.
        raise DataError("attested counter is older than the stored counter")
    sync_round.set_attested(attested_counter, attested_mac)

    attested_counter, attested_mac = require_attested_round("sync")

    # THE BASELINE IS THE DEVICE'S OWN HEAD, never one the answer names. A backend-chosen starting
    # point would let the walk begin at a state this device never reached.
    running_counter = counter
    running_root = root
    k_auth = await derive_k_auth()
    crossed = []
    for link in answer.links:
        running_counter, running_root = verify_chain_step(
            k_auth,
            ward_id,
            running_counter,
            running_root,
            (
                link.from_counter,
                link.from_root or None,
                link.to_counter,
                link.to_root or None,
                link.auth_commit,
            ),
        )
        # After the step verified, never before: an unverified commitment is just a claim.
        crossed.append(link.auth_commit)

    if running_counter != attested_counter:
        raise DataError("chain does not end at the attested counter")

    await verify_head_mac(attested_counter, attested_mac, running_root, subject="chain end")

    # The shared tail -- settle, persist, latch, close. The crossed commitments are passed so
    # settlement is exact: a claim landed when its OWN authorisation is among them, which is not
    # the same question as whether the counter moved past it.
    await adopt(attested_counter, running_root, landed_commits=crossed)


async def become_ready() -> bool:
    """Drive one sync if this session is not already online. Returns whether it now is.

    EXACTLY ONE ATTEMPT, no retry loop. A sync that fails to make the session online has been
    answered by a daemon that is not going to do better on a second identical ask, and a loop here
    would turn a disagreement into a hang in front of the user.
    """
    from . import round as sync_round

    if sync_round.is_online():
        return True

    await sync()
    return sync_round.is_online()


# --- publishing a mutation ----------------------------------------------------------------
#
# WHAT THIS REMOVES IS THE UNCONFIRMED WINDOW. On a connect build a write ends by handing the leaf
# to the host and hoping: the host must publish to the WM, then run a whole sync round before the
# device will believe its own write landed, and everything between is a state only the host knows.
# Here the device hands the mutation to the party that owns the replica and gets the attestation
# back in the same exchange.
#
# STRICTLY STRONGER THAN RECONCILE, and in a way worth being precise about. Reconcile adopts any
# root that reproduces an attested mac -- which is sound, but the mac is merely REPRODUCIBLE by the
# device. Here the device minted the mac itself, before anyone else saw the transition, and requires
# the attestation to name that exact counter and that exact mac. There is no root to be persuaded
# about.
#
# THE NONCE IS PER PUBLICATION, not per session. It is what stops a WM (or a daemon relaying one)
# answering this write with an attestation of some earlier head it had already collected -- the
# signature has to cover a value minted after the transition existed.


async def publish(
    entry_key: bytes,
    identity: "protobuf.MessageType | None",
    content: "protobuf.MessageType | None",
    from_root: bytes | None,
    counter: int,
    new_root: bytes | None,
    step: bytes,
) -> None:
    """Hand one mutation to the service, and adopt it if the WM attests it. Raises otherwise.

    `counter` is the counter the transition REACHES, so it advances from `counter - 1`; the device
    only ever moves by one, which is why the service is not told where it came from and cannot
    choose a different baseline.

    THE LATCH DROPS BEFORE THE REQUEST GOES OUT. From that moment the device cannot say whether the
    daemon applied the mutation, and recording the doubt only on failure would leave the whole
    unknown window looking known. `adopt` restores it, so the ordinary cost is one round trip.

    A CONFLICT IS NOT AN AMBIGUITY, and the difference decides what happens to the channel. The
    service says the WM's head was not the one this transition was built on -- so the write is known
    NOT to have landed, `_rpc` leaves the channel up because nothing about the conversation is
    unclear, and the operation fails cleanly. Everything else -- no answer, a wrong session, a type
    that does not belong -- may have landed, so `_rpc` tears the channel down and the outcome is
    settled by the next sync instead.

    NOTHING IS DONE HERE TO REOPEN A QUEUED OFFER, and that is not an omission. A conflict leaves
    the session offline, so the next WARD operation drives a sync, and that sync's `adopt` settles
    every outstanding claim by the commitments it actually crossed -- this one among them, and
    exactly as not-landed. Reopening it here would mean deciding the fate of one claim from a path
    that cannot see the others, which is how a claim for a change that DID land gets cleared.
    """
    from trezor.crypto import random
    from trezor.messages import WardPublish, WardPublishAck, WardPublishConflict
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import adopt, verify_round_attestation
    from .attest import NONCE_LENGTH, root_mac
    from .cas import wm_sig
    from .keys import derive_k_mac, derive_k_sig, derive_ward_id

    ward_id = await derive_ward_id()
    k_mac = await derive_k_mac()

    # BOTH HEADS ARE COMPUTED HERE, from the device's own key, and `to_mac` is the value the
    # attestation below is required to name. A mac passed in by the caller would be a mac the check
    # merely echoes.
    from_mac = root_mac(k_mac, ward_id, counter - 1, from_root)
    to_mac = root_mac(k_mac, ward_id, counter, new_root)

    nonce = random.bytes(NONCE_LENGTH)
    sync_round.begin(nonce)
    sync_round.mark_offline()

    answer = await _rpc(
        WardPublish(
            entry_key=entry_key,
            identity=identity,
            content=content,
            counter=counter,
            mac=to_mac,
            auth_commit=step,
            # OVER MAC HEADS, never roots: it is what the WM stores, and it is all the WM is ever
            # shown. The device authorises the advance without the freshness authority learning
            # anything about the tree.
            wm_sig=wm_sig(
                await derive_k_sig(), ward_id, counter - 1, from_mac, counter, to_mac
            ),
            nonce=nonce,
        ),
        WardPublishAck,
        WardPublishConflict,
    )

    # Compared by wire type rather than `isinstance` -- see `fetch`.
    if answer.MESSAGE_WIRE_TYPE == WardPublishConflict.MESSAGE_WIRE_TYPE:
        raise DataError("WARD: another writer moved the head first; retry")

    # The nonce binding, checked by the same code the sync route uses. What it does NOT check is
    # which head was attested -- that is the next two lines, and it is the whole strength of this
    # route.
    attested_counter, attested_mac = await verify_round_attestation(answer)
    if attested_counter != counter or attested_mac != to_mac:
        # The WM vouched for something, but not for this. No `require_attested_round` here and no
        # intermediate ATTESTED state: that machinery exists so a route which establishes its root
        # SEPARATELY can be joined to an attestation across a host turn, and this route has neither
        # a separate root nor a turn to cross -- the counter and mac are the device's own and are
        # compared directly, which is stricter than anything the state could add.
        raise DataError("the attestation does not name the head this device published")

    # Settle, then a checked `set_root`, then latch, then close -- see `adopt`. The crossed
    # commitment is this transition's own, so a queued change is settled by ITS authorisation
    # landing rather than by the counter having moved past it.
    await adopt(counter, new_root, landed_commits=[step])
