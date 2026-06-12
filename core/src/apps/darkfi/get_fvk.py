from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DarkfiFullViewingKey, DarkfiGetFullViewingKey


async def get_fvk(msg: DarkfiGetFullViewingKey) -> DarkfiFullViewingKey:
    from trezor import TR
    from trezor.crypto import pallas
    from trezor.messages import DarkfiFullViewingKey
    from trezor.ui.layouts import confirm_action

    from . import account_spend_key

    # Exporting the FVK reveals the account's entire transaction history to the
    # holder (but not the ability to spend). Require an explicit confirmation.
    await confirm_action(
        "darkfi_export_fvk",
        TR.darkfi__export_full_viewing_key,
        description=TR.darkfi__export_fvk_warning,
        verb=TR.buttons__confirm,
    )

    sk = await account_spend_key(msg.account)

    ask = pallas.derive_ask(sk)
    ak = pallas.spend_auth_pubkey(ask)
    nk = pallas.derive_nk(sk)

    return DarkfiFullViewingKey(ak=ak, nk=nk)
