from micropython import const

from trezor import ui
from trezor.messages import AuthorizeCoinJoin, Success
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_action, confirm_coinjoin

from apps.common import authorization
from apps.common.paths import validate_path

from .authorization import FEE_PER_ANONYMITY_DECIMALS
from .common import BIP32_WALLET_DEPTH
from .keychain import validate_path_against_script_type, with_keychain
from .sign_tx.layout import format_coin_amount

if False:
    from trezor import wire
    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

_MAX_COORDINATOR_LEN = const(18)


@with_keychain
async def authorize_coinjoin(
    ctx: wire.Context, msg: AuthorizeCoinJoin, keychain: Keychain, coin: CoinInfo
) -> Success:
    if len(msg.coordinator) > _MAX_COORDINATOR_LEN or not all(
        32 <= ord(x) <= 126 for x in msg.coordinator
    ):
        raise wire.DataError("Invalid coordinator name.")

    if not msg.address_n:
        raise wire.DataError("Empty path not allowed.")

    validation_path = msg.address_n + [0] * BIP32_WALLET_DEPTH
    await validate_path(
        ctx,
        keychain,
        validation_path,
        validate_path_against_script_type(
            coin, address_n=validation_path, script_type=msg.script_type
        ),
    )

    await confirm_action(
        ctx,
        "coinjoin_coordinator",
        title="Authorize CoinJoin",
        description="Do you really want to take part in a CoinJoin transaction at:\n{}",
        description_param=msg.coordinator,
        description_param_font=ui.MONO,
        icon=ui.ICON_RECOVERY,
    )

    if msg.fee_per_anonymity:
        fee_per_anonymity: str | None = format_amount(
            msg.fee_per_anonymity, FEE_PER_ANONYMITY_DECIMALS
        )
    else:
        fee_per_anonymity = None

    await confirm_coinjoin(
        ctx,
        fee_per_anonymity,
        format_coin_amount(msg.max_total_fee, coin, msg.amount_unit),
    )

    authorization.set(msg)

    return Success(message="CoinJoin authorized")
