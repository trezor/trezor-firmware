from micropython import const

import storage.cache
from trezor import ui
from trezor.messages.AuthorizeCoinJoin import AuthorizeCoinJoin
from trezor.messages.Success import Success
from trezor.strings import format_amount
from trezor.ui.text import Text

from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.common.paths import validate_path

from . import addresses
from .authorization import CoinJoinAuthorization
from .common import BIP32_WALLET_DEPTH
from .keychain import get_keychain_for_coin

if False:
    from trezor import wire

_MAX_COORDINATOR_LEN = const(18)


async def authorize_coinjoin(ctx: wire.Context, msg: AuthorizeCoinJoin,) -> Success:
    keychain, coin = await get_keychain_for_coin(ctx, msg.coin_name)

    if len(msg.coordinator) > _MAX_COORDINATOR_LEN or any(
        ord(x) < 32 or ord(x) > 126 for x in msg.coordinator
    ):
        raise wire.DataError("Invalid coordinator name.")

    await validate_path(
        ctx,
        addresses.validate_full_path,
        keychain,
        msg.address_n + [0] * BIP32_WALLET_DEPTH,
        coin.curve_name,
        coin=coin,
        script_type=msg.script_type,
    )

    text = Text("Authorize CoinJoin", ui.ICON_RECOVERY)
    text.normal("Do you really want to")
    text.normal("take part in a CoinJoin")
    text.normal("transaction at:")
    text.mono_bold(msg.coordinator)
    await require_confirm(ctx, text)

    text = Text("Authorize CoinJoin", ui.ICON_RECOVERY)
    text.normal("Amount to mix:")
    text.bold("%s %s" % (format_amount(msg.amount, coin.decimals), coin.coin_shortcut))
    text.normal("Maximum total fees:")
    text.bold("%s %s" % (format_amount(msg.max_fee, coin.decimals), coin.coin_shortcut))
    await require_hold_to_confirm(ctx, text)

    authorization = storage.cache.get(
        storage.cache.APP_BITCOIN_COINJOIN_AUTHORIZATION
    )  # type: CoinJoinAuthorization
    if authorization:
        authorization.__del__()
    authorization = CoinJoinAuthorization(msg, keychain, coin)
    storage.cache.set(storage.cache.APP_BITCOIN_COINJOIN_AUTHORIZATION, authorization)

    return Success(message="CoinJoin authorized")
