from ubinascii import hexlify

from trezor import wire
from trezor.messages import AmountUnit
from trezor.messages.SignStake import SignStake
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import Text

from apps.bitcoin.sign_tx.layout import format_coin_amount
from apps.common.coininfo import CoinInfo
from apps.common.confirm import require_confirm


async def require_confirm_sign_stake(
    ctx: wire.GenericContext, coin: CoinInfo, msg: SignStake
) -> None:
    coin_shortcut = coin.coin_shortcut
    page1 = Text("Sign " + coin_shortcut + " stake 1/3")
    page1.normal("Tx Id:")
    page1.mono(hexlify(msg.txid).decode())
    page1.normal("Output index:")
    page1.bold(str(msg.index))

    page2 = Text("Sign " + coin_shortcut + " stake 2/3")
    page2.normal("Amount:")
    page2.bold(format_coin_amount(msg.amount, coin, AmountUnit.BITCOIN))
    page2.normal("Height:")
    page2.bold(str(msg.height))
    page2.normal("Coinbase:")
    page2.bold("Yes" if msg.is_coinbase else "No")

    page3 = Text("Sign " + coin_shortcut + " stake 3/3")
    page3.normal("Prood Id:")
    page3.mono(hexlify(msg.proofid).decode())

    return await require_confirm(ctx, Paginated([page1, page2, page3]))
