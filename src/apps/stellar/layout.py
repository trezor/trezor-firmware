from trezor import ui, utils
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text

from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.stellar import consts


async def require_confirm_init(ctx, address: str, network_passphrase: str):
    text = Text("Confirm Stellar", ui.ICON_SEND, icon_color=ui.GREEN)
    text.normal("Initialize singing with")
    text.mono(*split(address))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    network = get_network_warning(network_passphrase)
    if network:
        text = Text("Confirm network", ui.ICON_CONFIRM, icon_color=ui.GREEN)
        text.normal("Transaction is on")
        text.bold(network)
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_memo(ctx, memo_type: int, memo_text: str):
    text = Text("Confirm memo", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    if memo_type == consts.MEMO_TYPE_TEXT:
        text.bold("Memo (TEXT)")
    elif memo_type == consts.MEMO_TYPE_ID:
        text.bold("Memo (ID)")
    elif memo_type == consts.MEMO_TYPE_HASH:
        text.bold("Memo (HASH)")
    elif memo_type == consts.MEMO_TYPE_RETURN:
        text.bold("Memo (RETURN)")
    else:  # MEMO_TYPE_NONE
        text.bold("No memo set!")
        text.normal("Important: Many exchanges require a memo when depositing")
    if memo_type != consts.MEMO_TYPE_NONE:
        text.mono(*split(memo_text))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_final(ctx, fee: int, num_operations: int):
    op_str = str(num_operations) + " operation"
    if num_operations > 1:
        op_str += "s"
    text = Text("Final confirm", ui.ICON_SEND, icon_color=ui.GREEN)
    text.normal("Sign this transaction")
    text.normal("made up of " + op_str)
    text.bold("and pay " + format_amount(fee))
    text.normal("for fee?")
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


def format_amount(amount: int, ticker=True) -> str:
    t = ""
    if ticker:
        t = " XLM"
    return utils.format_amount(amount, consts.AMOUNT_DIVISIBILITY) + t


def split(text):
    return utils.chunks(text, 17)


def trim(payload: str, length: int, dots=True) -> str:
    if len(payload) > length:
        if dots:
            return payload[: length - 2] + ".."
        return payload[: length - 2]
    return payload


def trim_to_rows(payload: str, rows: int = 1) -> str:
    return trim(payload, rows * 17)


def get_network_warning(network_passphrase: str):
    if network_passphrase == consts.NETWORK_PASSPHRASE_PUBLIC:
        return None
    if network_passphrase == consts.NETWORK_PASSPHRASE_TESTNET:
        return "testnet network"
    return "private network"
