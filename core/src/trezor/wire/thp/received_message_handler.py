from typing import TYPE_CHECKING

from storage.cache_thp import update_session_last_used
from trezor import utils
from trezor.enums import FailureType
from trezor.messages import Failure

from . import ChannelState, SessionState, ThpUnallocatedSessionError, session_manager
from .session_context import SeedlessSessionContext

if TYPE_CHECKING:
    from trezor.wire.protocol_common import Message

    from .channel import Channel

if __debug__:
    from trezor import log


async def handle_received_message(channel: Channel) -> bool:
    """
    Handle a message received from the channel.
    """
    try:
        if channel.state == ChannelState.ENCRYPTED_TRANSPORT:
            return await _handle_state_ENCRYPTED_TRANSPORT(channel)
        else:
            await _handle_pairing(channel)
    except ThpUnallocatedSessionError as e:
        error_message = Failure(code=FailureType.ThpUnallocatedSession)
        await channel.write(error_message, e.session_id)
    return False


async def _handle_state_ENCRYPTED_TRANSPORT(channel: Channel) -> bool:
    if __debug__:
        log.debug(__name__, "handle_state_ENCRYPTED_TRANSPORT", iface=channel.iface)

    session_id, message = await channel.read()

    if utils.USE_WARD_SERVICE_CHANNEL and not _permitted_on_service_channel(
        channel, message
    ):
        # REFUSED AT THE RECEIVE BOUNDARY, not in a handler. The rule is about the direction of
        # the channel rather than about any one message, so the check belongs where messages
        # arrive: once the service is bound the device is the sole initiator, and anything
        # inbound that is not the reply a device-initiated request is waiting for is by
        # definition unsolicited. A handler-level check would have to be added to every handler
        # that exists and to every one added later.
        await channel.write(
            Failure(
                code=FailureType.DataError,
                message="not accepted on the WARD service channel",
            ),
            session_id,
        )
        return False

    if session_id not in channel.sessions:
        s = session_manager.get_session_from_cache(channel, session_id)
        if s is None:
            s = SeedlessSessionContext(channel, session_id)

        channel.sessions[session_id] = s

    elif channel.sessions[session_id].get_session_state() is SessionState.UNALLOCATED:
        raise ThpUnallocatedSessionError(session_id)

    s = channel.sessions[session_id]
    update_session_last_used(
        s.channel_id.to_bytes(2, "big"), s.session_id.to_bytes(1, "big")
    )
    return await s.handle(message)


async def _handle_pairing(channel: Channel) -> None:
    from .pairing_context import PairingContext

    channel.connection_context = PairingContext(channel)

    _session_id, message = await channel.read()
    await channel.connection_context.handle(message)


def _permitted_on_service_channel(channel: Channel, message: Message) -> bool:
    """Whether a host-initiated message may be dispatched on this channel.

    Only `WardServiceOpen`. NOT `EndSession` and NOT `Cancel`: both are host-initiated, and
    allowing either back would recreate the duplex race the single initiator exists to remove --
    the device cannot tell an unsolicited `Cancel` from the reply it is waiting for, because this
    stream has no request ids.

    SHAPE ONLY, NOT POLICY. Whether a daemon may actually bind -- is it the pinned one, is another
    binding still live -- is the handler's decision, and deliberately not duplicated here: a
    boundary that refused a second `WardServiceOpen` outright would answer a daemon reconnecting
    after a restart with a generic refusal, and there would be nowhere left to notice that the
    binding it collides with names a channel that no longer exists.

    Every other interface is unaffected, so this costs the wire path one predicate.
    """
    from trezor import wire
    from trezor.enums import MessageType

    if not utils.USE_WARD_SERVICE_THP or not wire.is_ward_interface(channel.iface):
        return True

    return message.type == MessageType.WardServiceOpen
