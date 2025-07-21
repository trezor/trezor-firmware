from typing import TYPE_CHECKING

from storage import cache_thp

from .session_context import (
    GenericSessionContext,
    SeedlessSessionContext,
    SessionContext,
)

if TYPE_CHECKING:
    from .thp_main import ThpContext


def get_new_session_context(
    ctx: ThpContext,
    session_id: int,
) -> SessionContext:
    channel_ctx = ctx.channel
    session_cache = cache_thp.create_or_replace_session(
        channel=channel_ctx.channel_cache,
        session_id=session_id.to_bytes(1, "big"),
    )
    return SessionContext(ctx, session_cache)


def get_new_seedless_session_ctx(
    ctx: ThpContext, session_id: int
) -> SeedlessSessionContext:
    """
    Creates new `SeedlessSessionContext` that is not backed by a cache entry.

    Seed cannot be derived with this type of session.
    """
    return SeedlessSessionContext(ctx, session_id)


def get_session_from_cache(
    ctx: ThpContext, session_id: int
) -> GenericSessionContext | None:
    """
    Returns a `SessionContext` (or `SeedlessSessionContext`) reconstructed from a cache or `None` if backing cache is not found.
    """
    channel_ctx = ctx.channel
    session_id_bytes = session_id.to_bytes(1, "big")
    session_cache = cache_thp.get_allocated_session(
        channel_ctx.channel_id, session_id_bytes
    )
    if session_cache is None:
        return None
    elif cache_thp.is_seedless_session(session_cache):
        return SeedlessSessionContext(ctx, session_id)
    return SessionContext(ctx, session_cache)
