from typing import TYPE_CHECKING

import storage.device as storage_device
from storage import common as storage_common
from storage.cache_common import APP_COMMON_SEED, APP_COMMON_SEED_WITHOUT_PASSPHRASE
from trezor import utils
from trezor.enums import ButtonRequestType
from trezor.messages import Success
from trezor.ui.layouts import confirm_action
from trezor.wire import DataError, context

from apps.common.seed import raise_if_not_initialized

if TYPE_CHECKING:
    from trezor.messages import SetPermanentPassphrase


async def set_permanent_passphrase(msg: SetPermanentPassphrase) -> Success:
    """Make the current passphrase-derived wallet the device's permanent root.

    The stored seed is overwritten with the 64-byte BIP-32 seed currently held
    in the session cache (seed + passphrase). The original mnemonic and all
    wallets derived from sibling passphrases are destroyed. The only way to leave
    permanent-passphrase mode is to wipe the device.
    """
    raise_if_not_initialized()

    # The current session must have derived a seed (i.e., the user must have
    # entered their PIN and, if applicable, their passphrase).
    derived_seed = context.cache_get(APP_COMMON_SEED)
    if derived_seed is None:
        raise DataError("No active session seed. Unlock the device first.")
    if len(derived_seed) != 64:
        raise DataError("Invalid seed length.")

    # Strong warning: this operation is irreversible. The original mnemonic
    # and all parent/sibling keys derived from it will be lost.
    #
    # We intentionally run on universal (non-Bitcoin-only) builds so Ethereum
    # and other BIP-32/BIP-39 coins keep working. Cardano is the outlier: its
    # Icarus derivation requires the original binary mnemonic metadata, which
    # we erase below, so we add a specific warning for it rather than blocking
    # the whole operation.
    description = (
        "The original seed and all parent/sibling keys will be permanently lost. "
        "You will need to wipe the device to recover normal seed mode. "
        "The seed check feature will no longer apply."
    )
    if not utils.BITCOIN_ONLY:
        description += (
            "\n\nThis device also supports Cardano. If you have used a Cardano "
            "wallet derived from the original seed, it will become inaccessible "
            "after this operation."
        )

    await confirm_action(
        "set_permanent_passphrase",
        title="Set permanent passphrase",
        action="This will overwrite the stored seed with the currently derived wallet.",
        description=description,
        reverse=True,
        verb="Hold to confirm",
        hold=True,
        hold_danger=True,
        br_code=ButtonRequestType.ProtectCall,
    )

    # Overwrite the stored mnemonic secret with the currently derived seed.
    # From now on the device behaves as if this derived sub-key were the root.
    storage_device.store_raw_seed_secret(derived_seed)

    # Compact the storage to physically erase the deleted mnemonic item,
    # including its header (which would otherwise reveal the old length).
    storage_common.compact()

    # Clear cached secrets so the next operation derives from the new root.
    context.cache_delete(APP_COMMON_SEED)
    context.cache_delete(APP_COMMON_SEED_WITHOUT_PASSPHRASE)

    return Success(message="Passphrase set as permanent.")
