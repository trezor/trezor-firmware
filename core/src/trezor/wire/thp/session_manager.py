from typing import TYPE_CHECKING

from storage import cache_thp

from .session_context import (
    GenericSessionContext,
    ManagementSessionContext,
    SessionContext,
)

if TYPE_CHECKING:
    from .channel import Channel


def create_new_session(channel_ctx: Channel) -> SessionContext:
    session_cache = cache_thp.get_new_session(channel_ctx.channel_cache)
    return SessionContext(channel_ctx, session_cache)


def create_new_management_session(
    channel_ctx: Channel, session_id: int = cache_thp.MANAGEMENT_SESSION_ID
) -> ManagementSessionContext:
    return ManagementSessionContext(channel_ctx, session_id)


def get_session_from_cache(
    channel_ctx: Channel, session_id: int
) -> GenericSessionContext | None:
    cached_sessions = cache_thp.get_allocated_sessions(channel_ctx.channel_id)
    for s in cached_sessions:
        print(s, s.channel_id, int.from_bytes(s.session_id, "big"))
        if (
            s.channel_id == channel_ctx.channel_id
            and int.from_bytes(s.session_id, "big") == session_id
        ):
            return SessionContext(channel_ctx, s)
    return None
