from typing import TYPE_CHECKING

from storage import cache_thp

from .session_context import (
    GenericSessionContext,
    SeedlessSessionContext,
    SessionContext,
    WardServiceSessionContext,
)

if TYPE_CHECKING:
    from .channel import Channel


def get_new_session_context(
    channel_ctx: Channel,
    session_id: int,
) -> SessionContext:
    session_cache = cache_thp.create_or_replace_session(
        channel_id=channel_ctx.channel_id_bytes(),
        session_id=session_id.to_bytes(1, "big"),
    )
    return SessionContext(channel_ctx, session_cache)


def get_session_from_cache(
    channel_ctx: Channel, session_id: int
) -> GenericSessionContext | None:
    """
    Returns a `SessionContext` (or `SeedlessSessionContext`) reconstructed from a cache or `None` if backing cache is not found.
    """
    session_id_bytes = session_id.to_bytes(1, "big")
    session_cache = cache_thp.get_allocated_session(
        channel_ctx.channel_id_bytes(), session_id_bytes
    )
    if session_cache is None:
        return None
    elif cache_thp.is_seedless_session(session_cache):
        return SeedlessSessionContext(channel_ctx, session_id)
    elif cache_thp.is_ward_service_session(session_cache):
        # DISPATCHED EXPLICITLY, because the fall-through below builds a WALLET session. The state
        # survives session restarts in the cache, so without this a service slot would come back as
        # an ordinary `SessionContext` and nothing would distinguish it from a wallet's.
        return WardServiceSessionContext(channel_ctx, session_cache)
    return SessionContext(channel_ctx, session_cache)
