from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.HederaAccountAmount import accountID
from trezor.messages.HederaSignTx import HederaSignTx
from trezor.strings import format_amount
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm, require_hold_to_confirm


def format_account(account: accountID) -> str:
    shard = account.shard
    realm = account.realm
    num = account.num
    return f"{shard}.{realm}.{num}"


async def confirm_account(ctx, account_id: str):
    text = Text("Confirm Account", ui.ICON_CONFIRM, ui.GREEN)
    text.bold(account_id)
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_create_account(ctx, initial_balance: str):
    text = Text("Create Account", ui.ICON_SEND, ui.BLUE)
    text.normal("Initial Balance:")
    text.bold(initial_balance)
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_transfer_hbar(ctx, msg: HederaSignTx):
    send_index = 0
    receive_index = 1

    if msg.tx.cryptoTransfer.transfers.accountAmounts[0].amount > 0:
        send_index = 1
        receive_index = 0

    operator = format_account(msg.tx.transactionID.accountID)
    sender = format_account(msg.tx.cryptoTransfer.transfers.accountAmounts[send_index])
    receiver = format_account(
        msg.tx.cryptoTransfer.transfers.accountAmounts[receive_index]
    )
    amount = format_amount(
        msg.tx.cryptoTransfer.transfers.accountAmounts[receive_index].amount, 8
    )
    fee = format_amount(msg.tx.fee, 8)
    memo = msg.tx.memo

    # Summary Page
    summaryPage = Text("Confirm Transfer", ui.ICON_SEND, ui.BLUE)
    summaryPage.bold("Asset: Hbar")

    # Operator Page
    operatorPage = Text("Operator", ui.ICON_SEND, ui.BLUE)
    operatorPage.bold(operator)

    # Sender
    senderPage = Text("Sender", ui.ICON_SEND, ui.BLUE)
    senderPage.bold(sender)

    # Receiver
    receiverPage = Text("Recipient", ui.ICON_SEND, ui.BLUE)
    receiverPage.bold(receiver)

    # Amount
    amountPage = Text("Amount", ui.ICON_SEND, ui.GREEN)
    amountPage.bold(amount)

    # Fee
    feePage = Text("Fee", ui.ICON_SEND, ui.BLUE)
    feePage.bold(fee)

    # Memo
    memoPage = Text("Memo", ui.ICON_SEND, ui.BLUE)
    memoPage.normal(memo)

    pages = [
        summaryPage,
        operatorPage,
        senderPage,
        receiverPage,
        amountPage,
        feePage,
        memoPage,
    ]

    paginated = Paginated(pages)
    await require_hold_to_confirm(ctx, paginated, ButtonRequestType.SignTx)


async def confirm_transfer_token(ctx, msg: HederaSignTx):
    send_index = 0
    receive_index = 1

    if msg.tx.cryptoTransfer.tokenTransfers[0].accountAmounts[0].amount > 0:
        send_index = 1
        receive_index = 0

    token = format_account(msg.tx.cryptoTransfer.tokenTransfers[0].token)
    operator = format_account(msg.tx.transactionID.accountID)
    sender = format_account(
        msg.tx.cryptoTransfer.tokenTransfers[0].accountAmounts[send_index].accountID
    )
    receiver = format_account(
        msg.tx.cryptoTransfer.tokenTransfers[0].accountAmounts[receive_index].accountID
    )
    amount = format_amount(
        msg.tx.cryptoTransfer.tokenTransfers[0].accountAmounts[receive_index].amount,
        msg.decimals,
    )
    fee = format_amount(msg.tx.fee, 8)
    memo = msg.tx.memo

    # Summary Page
    summaryPage = Text("Confirm Transfer", ui.ICON_SEND, ui.BLUE)
    summaryPage.bold(f"Asset: {token}")

    # Operator Page
    operatorPage = Text("Operator", ui.ICON_SEND, ui.BLUE)
    operatorPage.bold(operator)

    # Sender
    senderPage = Text("Sender", ui.ICON_SEND, ui.BLUE)
    senderPage.bold(sender)

    # Receiver
    receiverPage = Text("Recipient", ui.ICON_SEND, ui.BLUE)
    receiverPage.bold(receiver)

    # Amount
    amountPage = Text("Amount", ui.ICON_SEND, ui.GREEN)
    amountPage.bold(amount)

    # Fee
    feePage = Text("Fee", ui.ICON_SEND, ui.BLUE)
    feePage.bold(fee)

    # Memo
    memoPage = Text("Memo", ui.ICON_SEND, ui.BLUE)
    memoPage.normal(memo)

    pages = [
        summaryPage,
        operatorPage,
        senderPage,
        receiverPage,
        amountPage,
        feePage,
        memoPage,
    ]

    paginated = Paginated(pages)
    await require_hold_to_confirm(ctx, paginated, ButtonRequestType.SignTx)


async def confirm_associate_token(ctx, msg: HederaSignTx):
    token = format_account(msg.tx.tokenAssociate.tokens[0])
    account = format_account(msg.tx.tokenAssociate.account)
    text = Text("Associate token:", ui.ICON_CHECK, ui.GREEN)
    text.bold(token)
    text.normal("with account:")
    text.bold(account)
    await require_confirm(ctx, text, ButtonRequestType.SignTx)
