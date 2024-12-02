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
    """
    Creates new `SessionContext` backed by cache.
    """
    session_cache = cache_thp.get_new_session(channel_ctx.channel_cache)
    return SessionContext(channel_ctx, session_cache)


def create_new_management_session(
    channel_ctx: Channel, session_id: int = cache_thp.MANAGEMENT_SESSION_ID
) -> ManagementSessionContext:
    """
    Creates new `ManagementSessionContext` that is not backed by cache entry.

    Seed cannot be derived with this type of session.
    """
    return ManagementSessionContext(channel_ctx, session_id)


def get_session_from_cache(
    channel_ctx: Channel, session_id: int
) -> GenericSessionContext | None:
    """
    Returns a `SessionContext` (or `ManagementSessionContext`) reconstructed from a cache or `None` if backing cache is not found.
    """
    session_id_bytes = session_id.to_bytes(1, "big")
    session_cache = cache_thp.get_allocated_session(
        channel_ctx.channel_id, session_id_bytes
    )
    if session_cache is None:
        return None
    elif cache_thp.is_management_session(session_cache):
        return ManagementSessionContext(channel_ctx, session_id)
    return SessionContext(channel_ctx, session_cache)
