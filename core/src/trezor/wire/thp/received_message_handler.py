from typing import TYPE_CHECKING

from storage.cache_thp import update_session_last_used
from trezor.enums import FailureType
from trezor.messages import Failure

from . import ChannelState, SessionState, ThpUnallocatedSessionError, session_manager
from .session_context import SeedlessSessionContext

if TYPE_CHECKING:
    from .channel import Channel

if __debug__:
    from trezor import log


async def handle_received_message(channel: Channel) -> None:
    """
    Handle a message received from the channel.
    """
    try:
        if channel.state == ChannelState.ENCRYPTED_TRANSPORT:
            await _handle_state_ENCRYPTED_TRANSPORT(channel)
        else:
            await _handle_pairing(channel)
    except ThpUnallocatedSessionError as e:
        error_message = Failure(code=FailureType.ThpUnallocatedSession)
        await channel.write(error_message, e.session_id)


async def _handle_state_ENCRYPTED_TRANSPORT(ctx: Channel) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_ENCRYPTED_TRANSPORT", iface=ctx.iface)

    session_id, message = await ctx.read()
    if session_id not in ctx.sessions:

        s = session_manager.get_session_from_cache(ctx, session_id)

        if s is None:
            s = SeedlessSessionContext(ctx, session_id)

        ctx.sessions[session_id] = s

    elif ctx.sessions[session_id].get_session_state() is SessionState.UNALLOCATED:
        raise ThpUnallocatedSessionError(session_id)

    s = ctx.sessions[session_id]
    update_session_last_used(
        s.channel_id.to_bytes(2, "big"), (s.session_id).to_bytes(1, "big")
    )
    await s.handle(message)


async def _handle_pairing(ctx: Channel) -> None:
    from .pairing_context import PairingContext

    ctx.connection_context = PairingContext(ctx)

    _session_id, message = await ctx.read()
    await ctx.connection_context.handle(message)
