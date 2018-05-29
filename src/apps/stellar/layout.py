from apps.common.confirm import *
from apps.stellar.consts import AMOUNT_DIVISIBILITY
from apps.stellar.consts import NETWORK_PASSPHRASE_PUBLIC
from apps.stellar.consts import NETWORK_PASSPHRASE_TESTNET
from apps.stellar import helpers
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import chunks, format_amount


async def require_confirm_init(ctx, pubkey: bytes, network_passphrase: str):
    content = Text('Confirm Stellar', ui.ICON_SEND,
                   ui.NORMAL, 'Initialize singing with',
                   ui.MONO, *format_address(pubkey),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)
    network = get_network_warning(network_passphrase)
    if network:
        content = Text('Confirm network', ui.ICON_CONFIRM,
                       ui.NORMAL, 'Transaction is on',
                       ui.BOLD, network,
                       icon_color=ui.GREEN)
        await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def require_confirm_final(ctx, fee: int, num_operations: int):
    op_str = str(num_operations) + ' operation'
    if num_operations > 1:
        op_str += 's'
    content = Text('Final confirm', ui.ICON_SEND,
                   ui.NORMAL, 'Sign this transaction',
                   ui.NORMAL, 'made up of ' + op_str,
                   ui.BOLD, 'and pay ' + format_amount(fee, AMOUNT_DIVISIBILITY) + ' XLM',
                   ui.NORMAL, 'for fee?',
                   icon_color=ui.GREEN)
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await require_hold_to_confirm(ctx, content, ButtonRequestType.SignTx)


def format_address(pubkey: bytes) -> str:
    address = helpers.address_from_public_key(pubkey)
    return split_address(address)


def split_address(address):
    return chunks(address, 17)


def get_network_warning(network_passphrase: str):
    if network_passphrase == NETWORK_PASSPHRASE_PUBLIC:
        return None
    if network_passphrase == NETWORK_PASSPHRASE_TESTNET:
        return 'testnet network'
    return 'private network'
