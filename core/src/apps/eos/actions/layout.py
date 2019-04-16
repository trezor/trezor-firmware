from micropython import const
from ubinascii import hexlify

from trezor import ui, wire
from trezor.messages import (
    ButtonRequestType,
    EosActionBuyRam,
    EosActionBuyRamBytes,
    EosActionDelegate,
    EosActionDeleteAuth,
    EosActionLinkAuth,
    EosActionNewAccount,
    EosActionRefund,
    EosActionSellRam,
    EosActionTransfer,
    EosActionUndelegate,
    EosActionUnlinkAuth,
    EosActionUpdateAuth,
    EosActionVoteProducer,
    MessageType,
)
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.confirm import CONFIRMED, ConfirmDialog
from trezor.ui.scroll import Scrollpage, animate_swipe, paginate
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.eos import helpers
from apps.eos.get_public_key import _public_key_to_wif
from apps.eos.layout import require_confirm

_LINE_LENGTH = const(17)
_LINE_PLACEHOLDER = "{:<" + str(_LINE_LENGTH) + "}"
_FIRST_PAGE = const(0)
_TWO_FIELDS_PER_PAGE = const(2)
_THREE_FIELDS_PER_PAGE = const(3)
_FOUR_FIELDS_PER_PAGE = const(4)
_FIVE_FIELDS_PER_PAGE = const(5)


async def confirm_action_buyram(ctx, msg: EosActionBuyRam):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "Buy RAM"
    fields = []
    fields.append("Payer:")
    fields.append(helpers.eos_name_to_string(msg.payer))
    fields.append("Receiver:")
    fields.append(helpers.eos_name_to_string(msg.receiver))
    fields.append("Amount:")
    fields.append(helpers.eos_asset_to_string(msg.quantity))

    pages = list(chunks(fields, _FOUR_FIELDS_PER_PAGE))

    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)
    await ctx.wait(paginator)


async def confirm_action_buyrambytes(ctx, msg: EosActionBuyRamBytes):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "Buy RAM"
    fields = []
    fields.append("Payer:")
    fields.append(helpers.eos_name_to_string(msg.payer))
    fields.append("Receiver:")
    fields.append(helpers.eos_name_to_string(msg.receiver))
    fields.append("Bytes:")
    fields.append(str(msg.bytes))

    pages = list(chunks(fields, _FOUR_FIELDS_PER_PAGE))
    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)

    await ctx.wait(paginator)


async def confirm_action_delegate(ctx, msg: EosActionDelegate):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "Delegate"
    fields = []
    fields.append("Sender:")
    fields.append(helpers.eos_name_to_string(msg.sender))
    fields.append("Receiver:")
    fields.append(helpers.eos_name_to_string(msg.receiver))
    fields.append("CPU:")
    fields.append(helpers.eos_asset_to_string(msg.cpu_quantity))
    fields.append("NET:")
    fields.append(helpers.eos_asset_to_string(msg.net_quantity))

    if msg.transfer:
        fields.append("Transfer: Yes")
        fields.append("Receiver:")
        fields.append(helpers.eos_name_to_string(msg.receiver))
    else:
        fields.append("Transfer: No")

    pages = list(chunks(fields, _FOUR_FIELDS_PER_PAGE))
    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)

    await ctx.wait(paginator)


async def confirm_action_sellram(ctx, msg: EosActionSellRam):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "Sell RAM"
    fields = []
    fields.append("Receiver:")
    fields.append(helpers.eos_name_to_string(msg.account))
    fields.append("Bytes:")
    fields.append(str(msg.bytes))

    pages = list(chunks(fields, _TWO_FIELDS_PER_PAGE))
    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)

    await ctx.wait(paginator)


async def confirm_action_undelegate(ctx, msg: EosActionUndelegate):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "Undelegate"
    fields = []
    fields.append("Sender:")
    fields.append(helpers.eos_name_to_string(msg.sender))
    fields.append("Receiver:")
    fields.append(helpers.eos_name_to_string(msg.receiver))
    fields.append("CPU:")
    fields.append(helpers.eos_asset_to_string(msg.cpu_quantity))
    fields.append("NET:")
    fields.append(helpers.eos_asset_to_string(msg.net_quantity))

    pages = list(chunks(fields, _FOUR_FIELDS_PER_PAGE))
    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)

    await ctx.wait(paginator)


async def confirm_action_refund(ctx, msg: EosActionRefund):
    text = Text("Refund", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.normal("Owner:")
    text.normal(helpers.eos_name_to_string(msg.owner))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_action_voteproducer(ctx, msg: EosActionVoteProducer):
    if msg.proxy and not msg.producers:
        # PROXY
        text = Text("Vote for proxy", ui.ICON_CONFIRM, icon_color=ui.GREEN)
        text.normal("Voter:")
        text.normal(helpers.eos_name_to_string(msg.voter))
        text.normal("Proxy:")
        text.normal(helpers.eos_name_to_string(msg.proxy))
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)

    elif msg.producers:
        # PRODUCERS
        await ctx.call(
            ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
        )
        producers = list(enumerate(msg.producers))
        pages = list(chunks(producers, _FIVE_FIELDS_PER_PAGE))
        paginator = paginate(show_voter_page, len(pages), _FIRST_PAGE, pages)
        await ctx.wait(paginator)

    else:
        # Cancel vote
        text = Text("Cancel vote", ui.ICON_CONFIRM, icon_color=ui.GREEN)
        text.normal("Voter:")
        text.normal(helpers.eos_name_to_string(msg.voter))
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_action_transfer(ctx, msg: EosActionTransfer, account: str):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "Transfer"
    fields = []
    fields.append("From:")
    fields.append(helpers.eos_name_to_string(msg.sender))
    fields.append("To:")
    fields.append(helpers.eos_name_to_string(msg.receiver))
    fields.append("Amount:")
    fields.append(helpers.eos_asset_to_string(msg.quantity))
    fields.append("Contract:")
    fields.append(account)

    if msg.memo is not None:
        fields.append("Memo:")
        fields += split_data(msg.memo[:512])

    pages = list(chunks(fields, _FOUR_FIELDS_PER_PAGE))

    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)
    await ctx.wait(paginator)


async def confirm_action_updateauth(ctx, msg: EosActionUpdateAuth):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "Update Auth"
    fields = []
    fields.append("Account:")
    fields.append(helpers.eos_name_to_string(msg.account))
    fields.append("Permission:")
    fields.append(helpers.eos_name_to_string(msg.permission))
    fields.append("Parent:")
    fields.append(helpers.eos_name_to_string(msg.parent))
    fields += authorization_fields(msg.auth)

    pages = list(chunks(fields, _FOUR_FIELDS_PER_PAGE))

    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)
    await ctx.wait(paginator)


async def confirm_action_deleteauth(ctx, msg: EosActionDeleteAuth):
    text = Text("Delete auth", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.normal("Account:")
    text.normal(helpers.eos_name_to_string(msg.account))
    text.normal("Permission:")
    text.normal(helpers.eos_name_to_string(msg.permission))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_action_linkauth(ctx, msg: EosActionLinkAuth):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "Link Auth"
    fields = []
    fields.append("Account:")
    fields.append(helpers.eos_name_to_string(msg.account))
    fields.append("Code:")
    fields.append(helpers.eos_name_to_string(msg.code))
    fields.append("Type:")
    fields.append(helpers.eos_name_to_string(msg.type))
    fields.append("Requirement:")
    fields.append(helpers.eos_name_to_string(msg.requirement))

    pages = list(chunks(fields, _FOUR_FIELDS_PER_PAGE))
    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)

    await ctx.wait(paginator)


async def confirm_action_unlinkauth(ctx, msg: EosActionUnlinkAuth):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "Unlink Auth"
    fields = []
    fields.append("Account:")
    fields.append(helpers.eos_name_to_string(msg.account))
    fields.append("Code:")
    fields.append(helpers.eos_name_to_string(msg.code))
    fields.append("Type:")
    fields.append(helpers.eos_name_to_string(msg.type))

    pages = list(chunks(fields, _FOUR_FIELDS_PER_PAGE))
    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)

    await ctx.wait(paginator)


async def confirm_action_newaccount(ctx, msg: EosActionNewAccount):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )

    text = "New Account"
    fields = []
    fields.append("Creator:")
    fields.append(helpers.eos_name_to_string(msg.creator))
    fields.append("Name:")
    fields.append(helpers.eos_name_to_string(msg.name))
    fields += authorization_fields(msg.owner)
    fields += authorization_fields(msg.active)

    pages = list(chunks(fields, _FOUR_FIELDS_PER_PAGE))
    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)

    await ctx.wait(paginator)


async def confirm_action_unknown(ctx, action, checksum):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ConfirmOutput), MessageType.ButtonAck
    )
    text = "Arbitrary data"
    fields = []
    fields.append("Contract:")
    fields.append(helpers.eos_name_to_string(action.account))
    fields.append("Action Name:")
    fields.append(helpers.eos_name_to_string(action.name))

    fields.append("Checksum: ")
    fields += split_data(hexlify(checksum).decode("ascii"))

    pages = list(chunks(fields, _FIVE_FIELDS_PER_PAGE))
    paginator = paginate(show_lines_page, len(pages), _FIRST_PAGE, pages, text)

    await ctx.wait(paginator)


@ui.layout
async def show_lines_page(page: int, page_count: int, pages: list, header: str):
    if header == "Arbitrary data":
        text = Text(header, ui.ICON_WIPE, icon_color=ui.RED)
    else:
        text = Text(header, ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.mono(*pages[page])

    content = Scrollpage(text, page, page_count)
    if page + 1 == page_count:
        if await ConfirmDialog(content) != CONFIRMED:
            raise wire.ActionCancelled("Action cancelled")
    else:
        content.render()
        await animate_swipe()


@ui.layout
async def show_voter_page(page: int, page_count: int, pages: list):
    lines = [
        "{:2d}. {}".format(wi + 1, helpers.eos_name_to_string(producer))
        for wi, producer in pages[page]
    ]
    text = Text("Vote for producers", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.mono(*lines)
    content = Scrollpage(text, page, page_count)

    if page + 1 == page_count:
        if await ConfirmDialog(content) != CONFIRMED:
            raise wire.ActionCancelled("Action cancelled")
    else:
        content.render()
        await animate_swipe()


def authorization_fields(auth):
    fields = []

    fields.append("Threshold:")
    fields.append(str(auth.threshold))

    for i, key in enumerate(auth.keys):
        _key = _public_key_to_wif(bytes(key.key))
        _weight = str(key.weight)

        header = "Key #{}:".format(i + 1)
        w_header = "Key #{} Weight:".format(i + 1)
        fields.append(header)
        fields += split_data(_key)
        fields.append(w_header)
        fields.append(_weight)

    for i, account in enumerate(auth.accounts):
        _account = helpers.eos_name_to_string(account.account.actor)
        _permission = helpers.eos_name_to_string(account.account.permission)

        a_header = "Account #{}:".format(i + 1)
        p_header = "Acc Permission #{}:".format(i + 1)
        w_header = "Account #{} weight:".format(i + 1)

        fields.append(a_header)
        fields.append(_account)
        fields.append(p_header)
        fields.append(_permission)
        fields.append(w_header)
        fields.append(str(account.weight))

    for i, wait in enumerate(auth.waits):
        _wait = str(wait.wait_sec)
        _weight = str(wait.weight)

        header = "Delay #{}".format(i + 1)
        w_header = "Delay #{} weight:".format(i + 1)
        fields.append(header)
        fields.append("{} sec".format(_wait))
        fields.append(w_header)
        fields.append(_weight)

    return fields


def split_data(data):
    temp_list = []
    len_left = len(data)
    while len_left > 0:
        temp_list.append("{} ".format(data[:_LINE_LENGTH]))
        data = data[_LINE_LENGTH:]
        len_left = len(data)
    return temp_list
