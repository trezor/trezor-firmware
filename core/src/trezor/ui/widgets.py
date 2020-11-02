from trezor import utils, wire

from .components.common.confirm import CONFIRMED

if False:
    from typing import Any, Awaitable

    from . import WidgetType

# NOTE: using any import magic probably causes mypy not to check equivalence of
#       widget type signatures across models
if utils.MODEL == "1":
    from .components.t1.widgets import (
        confirm_action,
        confirm_backup,
        confirm_change_count_over_threshold,
        confirm_feeoverthreshold,
        confirm_joint_total,
        confirm_nondefault_locktime,
        confirm_output,
        confirm_path_warning,
        confirm_reset_device,
        confirm_total,
        confirm_wipe,
        show_address,
    )
elif utils.MODEL == "T":
    from .components.tt.widgets import (  # noqa: F401
        confirm_action,
        confirm_backup,
        confirm_metadata,
        confirm_hex,
        confirm_joint_total,
        confirm_output,
        confirm_path_warning,
        confirm_reset_device,
        confirm_total,
        confirm_wipe,
        show_address,
    )
else:
    raise ValueError("Unknown Trezor model")


async def require(a: WidgetType) -> None:
    result = await a
    if result is not CONFIRMED:
        raise wire.ActionCancelled
