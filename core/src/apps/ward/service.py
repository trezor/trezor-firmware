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
    from trezor.messages import WardServiceOpen, WardServiceOpenAck


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

    # NEVER DISPLACE A LIVE SERVICE. A second open from the pinned daemon is either a duplicate or
    # a daemon that lost track of its own state; both are safer refused than allowed to replace a
    # binding some in-flight operation is holding.
    #
    # LIVE, not merely recorded. A daemon restart leaves a binding naming a channel that is gone,
    # and refusing on that would lock the service out until the device rebooted -- so a recorded
    # binding only counts while its channel is still open.
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

    return WardServiceOpenAck()
