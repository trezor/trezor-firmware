"""The WARD service channel: a daemon that owns the replica, on an interface of its own.

DEPRECATED, AND OFF BY DEFAULT (`--enable-ward-service-channel`); do not build new work on it. It
has no recovery route -- no `WardRollback`, and `sync` is chain-only -- so a daemon with incomplete
history leaves the device out of sync with nothing to do about it.

What it buys: the device can ASK rather than only answer, at any point in any workflow.
`WardServiceOpen` is the last host-initiated message; afterwards the device is the sole initiator,
because one stream without request ids cannot carry two conversations. Binding names WHICH daemon
and nothing else -- readiness comes from a sync. See `docs/core/misc/ward-channels.md`.
"""

from micropython import const
from typing import TYPE_CHECKING

from trezor import utils

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import WireInterface

    from trezor import protobuf
    from trezor.messages import WardEntryAck, WardServiceOpen, WardServiceOpenAck
    from trezor.protobuf import MessageType as LoadedMessageType
    from trezor.wire.codec.ward_context import WardCodecContext
    from trezor.wire.protocol_common import Message
    from trezor.wire.thp.channel import Channel

    ServiceLink = Channel | WardCodecContext


# End-to-end bound on one reverse RPC, covering the WRITE too: under THP a write to a vanished
# daemon waits on retransmissions for far longer than this. A hang is the one non-fail-closed
# failure.
RPC_TIMEOUT_MS = const(30_000)

# Bumped when the message set changes shape, so an older daemon is refused by name.
PROTOCOL_VERSION = 1


def _binding_cache():
    from storage.cache import get_sessionless_cache

    return get_sessionless_cache()


def get_binding() -> tuple[int, int, int] | None:
    """(iface_num, channel_id, session_id) of the bound service, or None. All three are needed:
    channel ids are reallocated, possibly on another interface."""
    from storage.cache_common import APP_WARD_SERVICE

    raw = _binding_cache().get(APP_WARD_SERVICE)
    if raw is None:
        return None
    # iface(1) || channel_id(2) || session_id(1)
    return raw[0], int.from_bytes(raw[1:3], "big"), raw[3]


def set_binding(iface_num: int, channel_id: int, session_id: int) -> None:
    from storage.cache_common import APP_WARD_SERVICE

    _binding_cache().set(
        APP_WARD_SERVICE,
        bytes([iface_num]) + channel_id.to_bytes(2, "big") + bytes([session_id]),
    )


def clear_binding() -> None:
    """Forget which channel is the service. Does NOT unpin the daemon's key."""
    from storage.cache_common import APP_WARD_SERVICE

    _binding_cache().delete(APP_WARD_SERVICE)


def _check_open(iface: "WireInterface", msg: "WardServiceOpen") -> None:
    """What every bind refuses first: a connect build, a foreign interface, another protocol.
    The interface is the authorisation boundary -- a separate OS claim Suite does not hold."""
    from trezor import wire

    if not utils.USE_WARD_SERVICE_CHANNEL:
        raise wire.DataError("this firmware does not serve WARD over a service channel")
    if not wire.is_ward_interface(iface):
        raise wire.DataError("WARD service must be opened on the WARD interface")
    if msg.protocol_version != PROTOCOL_VERSION:
        raise wire.DataError("unsupported WARD service protocol version")


if utils.USE_WARD_SERVICE_THP:

    async def service(msg: WardServiceOpen) -> WardServiceOpenAck:
        """Bind this channel as the WARD service, pinning the daemon's static key on first use.

        Needs no pre-existing service session: this handler allocates it.
        """
        from storage import cache_thp
        from storage import ward as storage_ward
        from trezor import wire
        from trezor.messages import WardServiceOpenAck
        from trezor.wire import context

        ctx = context.get_context()
        _check_open(ctx.iface, msg)

        channel = ctx.channel

        # ONE DAEMON, PINNED: every paired host -- Suite included -- passes pairing.
        host_key = channel.get_host_static_public_key()
        pinned = storage_ward.get_service_host_key()
        if pinned is None:
            # Pinning is a flash write; re-binding a pinned daemon writes nothing and works locked.
            from trezor import config

            if not config.is_unlocked():
                raise wire.DataError("unlock the device to bind the WARD service")
            storage_ward.set_service_host_key(host_key)
        elif pinned != host_key:
            raise wire.DataError("another daemon is bound as the WARD service")

        # Never displace a LIVE binding (a dead one is a daemon restart). Unreachable today, but
        # only because of properties of other code.
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

        # The conversation inverts: the dispatcher must stop reading, or it and the waiting
        # workflow would race for the same reply.
        channel.iface_ctx.release_dispatch()

        if __debug__:
            log.info(
                __name__,
                "service bound: cid %04x, session %d",
                ctx.channel_id,
                ctx.session_id,
                iface=ctx.iface,
            )

        return WardServiceOpenAck()

else:

    async def bind_codec(msg: WardServiceOpen, iface: WireInterface) -> WardServiceOpenAck:
        """Bind this interface as the WARD service. The codec has no identity to pin, so the
        interface is the whole check; nothing a daemon says is trusted anyway. Idempotent."""
        from trezor.messages import WardServiceOpenAck

        # The interface check is restated so the refusal does not depend on `wire.setup` routing.
        _check_open(iface, msg)

        set_binding(iface.iface_num(), 0, 0)

        if __debug__:
            log.info(__name__, "service bound", iface=iface)

        return WardServiceOpenAck()


# --- talking to the service ---------------------------------------------------------------
#
# EXACTLY ONE READER after binding. Under THP the dispatcher has released the channel and the
# waiting workflow reads; the codec's reader never lets go and routes answers into the workflow's
# mailbox (`trezor.wire.codec.ward_context`). An unsolicited message fails the type check in
# `_rpc` and fails that operation.


def _service_link() -> "tuple[ServiceLink, int]":
    """What an RPC talks through, and the session id to write on (0 where there is none).

    Under THP the channel is reattached every time: the `Channel` object does not survive
    session restarts, and a non-active channel cannot be written.
    """
    from trezor.wire import DataError

    bound = get_binding()
    if bound is None:
        raise DataError("no WARD service is bound")
    iface_num, channel_id, session_id = bound

    if not utils.USE_WARD_SERVICE_THP:
        from trezor.wire.codec.ward_context import service_link

        return service_link(), 0

    from trezor.wire import context

    # The current context is the wallet's channel, borrowed only for its `ThpContext`.
    thp_ctx = context.get_context().channel.iface_ctx.thp_ctx
    channel = thp_ctx.attach_existing_channel(iface_num, channel_id)

    if __debug__:
        log.debug(
            __name__,
            "channel %04x on iface %d attached for an RPC",
            channel_id,
            iface_num,
            iface=channel.iface,
        )

    return channel, session_id


async def _rpc(
    request: protobuf.MessageType, *expected: type[LoadedMessageType]
) -> "protobuf.MessageType":
    """Ask the service one question; the answer must be one of `expected`, on the service's own
    session. Anything else -- including silence -- tears the channel down (`_desynchronised`)."""
    from trezor import loop
    from trezor.wire.message_handler import decode_message

    link, session_id = _service_link()

    async def exchange() -> "tuple[int, Message] | str":
        # One deadline over write AND read; either can park forever on a silent daemon.
        if utils.USE_WARD_SERVICE_THP:
            await link.write(request, session_id)
            return await link.read()

        from trezor.wire.codec import ward_context

        try:
            return (session_id, await ward_context.exchange(request))
        except Exception as exc:
            if __debug__:
                log.exception(__name__, exc, iface=link.iface)
            return "the WARD service link failed"

    if __debug__:
        log.info(
            __name__,
            "(cid: %04x) asking the service: %s",
            link.channel_id,
            request.MESSAGE_NAME,
            iface=link.iface,
        )

    # `loop.sleep` returns an int, the exchange a tuple -- which is how the race is decided.
    answer = await loop.race(exchange(), loop.sleep(RPC_TIMEOUT_MS))
    if not isinstance(answer, tuple):
        raise _desynchronised(
            link,
            answer if isinstance(answer, str) else "the WARD service did not answer",
        )

    reply_session_id, message = answer
    if reply_session_id != session_id:
        message.release()
        raise _desynchronised(link, "WARD service answered on another session")

    for expected_type in expected:
        if message.type == expected_type.MESSAGE_WIRE_TYPE:
            if __debug__:
                log.info(
                    __name__,
                    "(cid: %04x) service answered: %s",
                    link.channel_id,
                    expected_type.MESSAGE_NAME,
                    iface=link.iface,
                )
            return decode_message(message, expected_type)

    if __debug__:
        log.error(
            __name__,
            "(cid: %04x) service answered with wire type %d; expected one of %s",
            link.channel_id,
            message.type,
            ", ".join([str(e.MESSAGE_WIRE_TYPE) for e in expected]),
            iface=link.iface,
        )

    message.release()
    raise _desynchronised(link, "unexpected message from the WARD service")


def _desynchronised(link: "ServiceLink", what: str) -> Exception:
    """Tear the service channel down and return the error to raise.

    The device is the sole initiator, so nothing else would ever resynchronise the conversation;
    under THP closing also discards a pending retransmission. The pin is NOT touched -- a dropped
    cable is not an ownership migration.
    """
    from trezor.wire import DataError

    exc = DataError(what)

    if __debug__:
        log.error(
            __name__,
            "(cid: %04x) tearing down the service channel: %s",
            link.channel_id,
            what,
            iface=link.iface,
        )

    clear_binding()
    if utils.USE_WARD_SERVICE_THP:
        link.clear(exc)
    else:
        from trezor.wire.codec import ward_context

        ward_context.tear_down(what)
    return exc


async def fetch(entry_key: bytes, retry: bool = True) -> "WardEntryAck":
    """Ask the service for its leaf at this path. Verifies NOTHING -- the caller does that.

    Names the device's head so the service can answer `WardSyncRequired`, which needs no
    authentication: lying about it only forces an authenticated sync. One sync, one retry.
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

    # By wire type: C-backed message classes are not valid `isinstance` arguments.
    if answer.MESSAGE_WIRE_TYPE == WardSyncRequired.MESSAGE_WIRE_TYPE:
        if retry:
            await sync()
            return await fetch(entry_key, retry=False)
        raise DataError("WARD service reports this device is out of sync")

    return answer


async def sync() -> None:
    """Ask the service for the current head and adopt it, or raise.

    One RPC for the connect path's three, reusing the same audited round (`round`, `adopt`). The
    nonce is minted here, before the daemon talks to the WM. CHAIN-ONLY: the daemon owns the
    history, so the head must descend from this device's own head and end exactly on the
    attested step.
    """
    from trezor.crypto import random
    from trezor.messages import WardSyncRequest, WardSyncResponse
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import adopt, verify_round_attestation
    from .attest import NONCE_LENGTH, same_root
    from .cas import head_init_sig, link_of, verify_chain_step
    from .common import require_initialized
    from .keys import derive_k_auth, derive_k_sig, derive_ward_id
    from .root import get_counter, get_root

    require_initialized()

    ward_id = await derive_ward_id()
    counter = await get_counter()
    root = await get_root()

    # Genesis-only enrolment: a `head_init_sig` proves a head genuine, never LATEST, so one
    # above counter 0 would let a WM be pinned to old state.
    init = None
    if counter == 0:
        init = head_init_sig(await derive_k_sig(), ward_id, counter, root)

    nonce = random.bytes(NONCE_LENGTH)
    sync_round.begin(nonce)

    answer = await _rpc(
        WardSyncRequest(
            nonce=nonce,
            ward_id=ward_id,
            current_counter=counter,
            current_root=root,
            head_init_sig=init,
        ),
        WardSyncResponse,
    )

    # Same verification as `ingest`; the WM may be several steps ahead, so both ends come off the
    # answer.
    (
        attested_from_counter,
        attested_from_root,
        attested_counter,
        attested_root,
    ) = await verify_round_attestation(
        answer.from_counter,
        answer.from_root or None,
        answer.from_head_nonce,
        answer.to_counter,
        answer.to_root or None,
        answer.to_head_nonce,
        answer.timestamp or 0,
        answer.wm_signature,
    )
    if attested_counter < counter:
        raise DataError("attested counter is older than the stored counter")
    sync_round.set_attested(
        attested_from_counter, attested_from_root, attested_counter, attested_root
    )

    # The baseline is the device's own head, never one the answer names.
    running_counter = counter
    running_root = root
    k_auth = await derive_k_auth()
    crossed = []
    reverts = 0
    last_from = None
    for link in answer.links:
        step = link_of(link)
        running_counter, running_root, reverted = verify_chain_step(
            k_auth, ward_id, running_counter, running_root, step
        )
        # After the step verified, never before.
        crossed.append(step[4])
        last_from = step[:2]
        reverts += reverted

    if __debug__:
        log.debug(__name__, "sync: %d links, %d of them reverts", len(answer.links), reverts)

    if running_counter != attested_counter:
        raise DataError("chain does not end at the attested counter")

    # And on the attested root (preimage form), or the fold could arrive at a fork.
    if not same_root(running_root, attested_root):
        raise DataError("chain end does not match the attested root")

    # And the last step must BE the attested step: a write and a revert can end on the same
    # (counter, root). With no links, the checks above already make the own head the attested one.
    if last_from is not None and (
        last_from[0] != attested_from_counter
        or not same_root(last_from[1], attested_from_root)
    ):
        raise DataError("the chain's last step is not the step the WM attested")

    await adopt(attested_counter, running_root, landed_commits=crossed)


async def become_ready() -> bool:
    """Drive ONE sync if this session is not already online; return whether it now is."""
    from . import round as sync_round

    if sync_round.is_online():
        return True

    await sync()
    return sync_round.is_online()


if utils.USE_WARD_SERVICE_THP:

    def close_bound_channel(reason: str) -> None:
        """Close the service's channel if still open, so the interface is free for the next daemon.

        Leaves the binding to the caller; silent when there is nothing reachable to close.
        """
        from trezor.wire import DataError

        bound = get_binding()
        if bound is None:
            return

        from trezorthp import channel_is_open

        if not channel_is_open(bound[1]):
            return

        try:
            channel, _session_id = _service_link()
        except DataError:
            return

        if __debug__:
            log.info(
                __name__,
                "(cid: %04x) closing the service channel: %s",
                channel.channel_id,
                reason,
                iface=channel.iface,
            )

        channel.clear(DataError(reason))


async def publish(
    entry_key: bytes,
    identity: "protobuf.MessageType | None",
    content: "protobuf.MessageType | None",
    from_root: bytes | None,
    counter: int,
    new_root: bytes | None,
    step: bytes,
    advance: bytes,
) -> None:
    """Hand one mutation `(counter - 1) -> counter` to the service and adopt it once the WM
    attests it; raise otherwise.

    The latch drops BEFORE the request: from then the outcome is unknown until `adopt`. A
    conflict means known-not-landed and keeps the channel; anything else may have landed and is
    settled by the next sync. Queued claims are left for that sync's `adopt` to settle.
    """
    from trezor.crypto import random
    from trezor.messages import WardPublish, WardPublishAck, WardPublishConflict
    from trezor.wire import DataError

    from . import round as sync_round
    from .adopt import adopt, verify_round_attestation
    from .attest import NONCE_LENGTH

    # The nonce `advance` was signed under; the attestation must name it as consumed.
    head_nonce = sync_round.require_head_nonce()

    # Per publication, so the WM cannot answer with an attestation collected earlier.
    nonce = random.bytes(NONCE_LENGTH)
    sync_round.begin(nonce)
    sync_round.mark_offline()

    answer = await _rpc(
        WardPublish(
            entry_key=entry_key,
            identity=identity,
            content=content,
            counter=counter,
            from_root=from_root,
            new_root=new_root,
            auth_commit=step,
            wm_sig=advance,
            nonce=nonce,
        ),
        WardPublishAck,
        WardPublishConflict,
    )

    if answer.MESSAGE_WIRE_TYPE == WardPublishConflict.MESSAGE_WIRE_TYPE:
        raise DataError("WARD: another writer moved the head first; retry")

    # EVERY OPERAND IS THE DEVICE'S OWN, nonce included: an attestation of any other head or any
    # other occurrence of this step fails as a bad signature.
    await verify_round_attestation(
        counter - 1,
        from_root,
        head_nonce,
        counter,
        new_root,
        answer.to_head_nonce,
        answer.timestamp or 0,
        answer.wm_signature,
    )

    await adopt(counter, new_root, landed_commits=[step])
