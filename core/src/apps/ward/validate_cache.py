from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDValidateCache, WARDValidateCacheAck


async def validate_cache(msg: WARDValidateCache) -> WARDValidateCacheAck:
    """WARDValidateCache wire handler (TA): check every cached WARD entry against the
    authenticated root, pulling one proof per entry. Counts only go back."""
    import storage.ward_store as ward_store
    from trezor.messages import WARDValidateCacheAck

    from apps.common import ward as core
    from apps.ward.keys import get_wallet_id

    checked, unchanged, updated, removed = await core.validate_cache()
    return WARDValidateCacheAck(
        checked=checked,
        unchanged=unchanged,
        updated=updated,
        removed=removed,
        counter=ward_store.get_counter(await get_wallet_id()),
    )
