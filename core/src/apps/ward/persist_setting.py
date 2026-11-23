"""The user's choice, per wallet, to let `WardCatchUp` persist a head while the WM is unreachable.

Allowing is held to confirm and names its cost; withdrawing needs no screen, since it only makes the
device stricter. Meaningless on a firmware built without a WM, which always persists.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardSetPersistWithoutWm


async def persist_setting(msg: WardSetPersistWithoutWm) -> Success:
    """Allow or stop `WardCatchUp` persisting a cached-attested head for the active wallet."""
    import storage.ward as ward_store
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import has_wm, require_initialized
    from .keys import derive_wallet_id

    # Before anything that needs a seed: the answer is a property of the build, which is also how
    # the test suite tells the two builds apart.
    if not has_wm():
        raise DataError("WARD: this firmware has no WARD Manager; catch-up always persists")
    require_initialized()

    if msg.allow:
        props = [
            (
                "Effect",
                "While the WARD Manager is unreachable, this Trezor keeps the newest state it last attested.",
                False,
            ),
            (
                "Warning",
                "If a change was reverted since, this Trezor may keep the reverted state until you revert again.",
                False,
            ),
        ]
        await confirm_properties(
            "ward_persist_without_wm", "Keep state without WM", props, hold=True
        )

    if not ward_store.set_setting(
        await derive_wallet_id(), ward_store.SETTING_PERSIST_WITHOUT_WM, msg.allow
    ):
        raise DataError("WARD: no settings slot for this wallet; eight already hold one")

    return Success(
        message="Persisting without the WM allowed" if msg.allow else "Persisting without the WM stopped"
    )
