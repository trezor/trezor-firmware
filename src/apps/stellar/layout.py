from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.stellar import consts
from apps.stellar import helpers
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor import utils


async def require_confirm_init(ctx, pubkey: bytes, network_passphrase: str):
    content = Text('Confirm Stellar', ui.ICON_SEND,
                   ui.NORMAL, 'Initialize singing with',
                   ui.MONO, *split(format_address(pubkey)),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)
    network = get_network_warning(network_passphrase)
    if network:
        content = Text('Confirm network', ui.ICON_CONFIRM,
                       ui.NORMAL, 'Transaction is on',
                       ui.BOLD, network,
                       icon_color=ui.GREEN)
        await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def require_confirm_memo(ctx, memo_type: int, memo_text: str):
    if memo_type == consts.MEMO_TYPE_TEXT:
        title = 'Memo (TEXT)'
    elif memo_type == consts.MEMO_TYPE_ID:
        title = 'Memo (ID)'
    elif memo_type == consts.MEMO_TYPE_HASH:
        title = 'Memo (HASH)'
    elif memo_type == consts.MEMO_TYPE_RETURN:
        title = 'Memo (RETURN)'
    else:  # MEMO_TYPE_NONE
        title = 'No memo set!'  # todo format this as ui.NORMAL not MONO
        memo_text = 'Important: Many exchanges require a memo when depositing'
    content = Text('Confirm memo', ui.ICON_CONFIRM,
                   ui.BOLD, title,
                   ui.MONO, *split(memo_text),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def require_confirm_final(ctx, fee: int, num_operations: int):
    op_str = str(num_operations) + ' operation'
    if num_operations > 1:
        op_str += 's'
    content = Text('Final confirm', ui.ICON_SEND,
                   ui.NORMAL, 'Sign this transaction',
                   ui.NORMAL, 'made up of ' + op_str,
                   ui.BOLD, 'and pay ' + format_amount(fee),
                   ui.NORMAL, 'for fee?',
                   icon_color=ui.GREEN)
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await require_hold_to_confirm(ctx, content, ButtonRequestType.SignTx)


def format_amount(amount: int, ticker=True) -> str:
    t = ''
    if ticker:
        t = ' XLM'
    return utils.format_amount(amount, consts.AMOUNT_DIVISIBILITY) + t


def format_address(pubkey: bytes) -> str:
    return helpers.address_from_public_key(pubkey)


# todo merge with nem
def split(text):
    return utils.chunks(text, 17)


# todo merge with nem
def trim(payload: str, length: int, dots=True) -> str:
    if len(payload) > length:
        if dots:
            return payload[:length - 2] + '..'
        return payload[:length - 2]
    return payload


# todo merge with nem
def trim_to_rows(payload: str, rows: int=1) -> str:
    return trim(payload, rows * 17)


def get_network_warning(network_passphrase: str):
    if network_passphrase == consts.NETWORK_PASSPHRASE_PUBLIC:
        return None
    if network_passphrase == consts.NETWORK_PASSPHRASE_TESTNET:
        return 'testnet network'
    return 'private network'
