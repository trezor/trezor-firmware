from micropython import const

from trezor import ui
from trezor.messages import AuthorizeCoinJoin, Success
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_action, confirm_coinjoin

from apps.base import set_authorization
from apps.common.paths import validate_path

from .authorization import FEE_PER_ANONYMITY_DECIMALS, CoinJoinAuthorization
from .common import BIP32_WALLET_DEPTH
from .keychain import get_keychain_for_coin, validate_path_against_script_type
from .sign_tx.layout import format_coin_amount

if False:
    from trezor import wire

_MAX_COORDINATOR_LEN = const(18)


async def authorize_coinjoin(ctx: wire.Context, msg: AuthorizeCoinJoin) -> Success:
    # We cannot use the @with_keychain decorator here, because we need the keychain
    # to survive the function exit. The ownership of the keychain is transferred to
    # the CoinJoinAuthorization object, which takes care of its destruction.
    keychain, coin = await get_keychain_for_coin(ctx, msg.coin_name)

    try:
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

        fee_per_anonymity = None
        if msg.fee_per_anonymity is not None:
            fee_per_anonymity = format_amount(
                msg.fee_per_anonymity, FEE_PER_ANONYMITY_DECIMALS
            )
        await confirm_coinjoin(
            ctx,
            fee_per_anonymity,
            format_coin_amount(msg.max_total_fee, coin, msg.amount_unit),
        )

        set_authorization(CoinJoinAuthorization(msg, keychain, coin))

    except BaseException:
        keychain.__del__()
        raise

    return Success(message="CoinJoin authorized")
