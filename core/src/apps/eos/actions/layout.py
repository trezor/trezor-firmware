from micropython import const
from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import Text
from trezor.utils import chunks

from .. import helpers
from ..layout import require_confirm

if False:
    from typing import List
    from trezor import wire
    from trezor.messages.EosAuthorization import EosAuthorization
    from trezor.messages.EosActionBuyRam import EosActionBuyRam
    from trezor.messages.EosActionBuyRamBytes import EosActionBuyRamBytes
    from trezor.messages.EosActionCommon import EosActionCommon
    from trezor.messages.EosActionDelegate import EosActionDelegate
    from trezor.messages.EosActionDeleteAuth import EosActionDeleteAuth
    from trezor.messages.EosActionLinkAuth import EosActionLinkAuth
    from trezor.messages.EosActionNewAccount import EosActionNewAccount
    from trezor.messages.EosActionRefund import EosActionRefund
    from trezor.messages.EosActionSellRam import EosActionSellRam
    from trezor.messages.EosActionTransfer import EosActionTransfer
    from trezor.messages.EosActionUndelegate import EosActionUndelegate
    from trezor.messages.EosActionUnlinkAuth import EosActionUnlinkAuth
    from trezor.messages.EosActionUpdateAuth import EosActionUpdateAuth
    from trezor.messages.EosActionVoteProducer import EosActionVoteProducer

_LINE_LENGTH = const(17)
_LINE_PLACEHOLDER = "{:<" + str(_LINE_LENGTH) + "}"
_FIRST_PAGE = const(0)
_TWO_FIELDS_PER_PAGE = const(2)
_THREE_FIELDS_PER_PAGE = const(3)
_FOUR_FIELDS_PER_PAGE = const(4)
_FIVE_FIELDS_PER_PAGE = const(5)


async def _require_confirm_paginated(
    ctx: wire.Context, header: str, fields: List[str], per_page: int
) -> None:
    pages = []
    for page in chunks(fields, per_page):
        if header == "Arbitrary data":
            text = Text(header, ui.ICON_WIPE, ui.RED)
        else:
            text = Text(header, ui.ICON_CONFIRM, ui.GREEN)
        text.mono(*page)
        pages.append(text)
    await require_confirm(ctx, Paginated(pages), ButtonRequestType.ConfirmOutput)


async def confirm_action_buyram(ctx: wire.Context, msg: EosActionBuyRam) -> None:
    text = "Buy RAM"
    fields = []
    fields.append("Payer:")
    fields.append(helpers.eos_name_to_string(msg.payer))
    fields.append("Receiver:")
    fields.append(helpers.eos_name_to_string(msg.receiver))
    fields.append("Amount:")
    fields.append(helpers.eos_asset_to_string(msg.quantity))
    await _require_confirm_paginated(ctx, text, fields, _FOUR_FIELDS_PER_PAGE)


async def confirm_action_buyrambytes(
    ctx: wire.Context, msg: EosActionBuyRamBytes
) -> None:
    text = "Buy RAM"
    fields = []
    fields.append("Payer:")
    fields.append(helpers.eos_name_to_string(msg.payer))
    fields.append("Receiver:")
    fields.append(helpers.eos_name_to_string(msg.receiver))
    fields.append("Bytes:")
    fields.append(str(msg.bytes))
    await _require_confirm_paginated(ctx, text, fields, _FOUR_FIELDS_PER_PAGE)


async def confirm_action_delegate(ctx: wire.Context, msg: EosActionDelegate) -> None:
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

    await _require_confirm_paginated(ctx, text, fields, _FOUR_FIELDS_PER_PAGE)


async def confirm_action_sellram(ctx: wire.Context, msg: EosActionSellRam) -> None:
    text = "Sell RAM"
    fields = []
    fields.append("Receiver:")
    fields.append(helpers.eos_name_to_string(msg.account))
    fields.append("Bytes:")
    fields.append(str(msg.bytes))
    await _require_confirm_paginated(ctx, text, fields, _TWO_FIELDS_PER_PAGE)


async def confirm_action_undelegate(
    ctx: wire.Context, msg: EosActionUndelegate
) -> None:
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
    await _require_confirm_paginated(ctx, text, fields, _FOUR_FIELDS_PER_PAGE)


async def confirm_action_refund(ctx: wire.Context, msg: EosActionRefund) -> None:
    text = Text("Refund", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.normal("Owner:")
    text.normal(helpers.eos_name_to_string(msg.owner))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_action_voteproducer(
    ctx: wire.Context, msg: EosActionVoteProducer
) -> None:
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
        text = "Vote for producers"
        fields = [
            "{:2d}. {}".format(wi + 1, helpers.eos_name_to_string(producer))
            for wi, producer in enumerate(msg.producers)
        ]
        await _require_confirm_paginated(ctx, text, fields, _FIVE_FIELDS_PER_PAGE)

    else:
        # Cancel vote
        text = Text("Cancel vote", ui.ICON_CONFIRM, icon_color=ui.GREEN)
        text.normal("Voter:")
        text.normal(helpers.eos_name_to_string(msg.voter))
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_action_transfer(
    ctx: wire.Context, msg: EosActionTransfer, account: str
) -> None:
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
        fields.extend(split_data(msg.memo[:512]))

    await _require_confirm_paginated(ctx, text, fields, _FOUR_FIELDS_PER_PAGE)


async def confirm_action_updateauth(
    ctx: wire.Context, msg: EosActionUpdateAuth
) -> None:
    text = "Update Auth"
    fields = []
    fields.append("Account:")
    fields.append(helpers.eos_name_to_string(msg.account))
    fields.append("Permission:")
    fields.append(helpers.eos_name_to_string(msg.permission))
    fields.append("Parent:")
    fields.append(helpers.eos_name_to_string(msg.parent))
    fields.extend(authorization_fields(msg.auth))
    await _require_confirm_paginated(ctx, text, fields, _FOUR_FIELDS_PER_PAGE)


async def confirm_action_deleteauth(
    ctx: wire.Context, msg: EosActionDeleteAuth
) -> None:
    text = Text("Delete auth", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.normal("Account:")
    text.normal(helpers.eos_name_to_string(msg.account))
    text.normal("Permission:")
    text.normal(helpers.eos_name_to_string(msg.permission))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_action_linkauth(ctx: wire.Context, msg: EosActionLinkAuth) -> None:
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
    await _require_confirm_paginated(ctx, text, fields, _FOUR_FIELDS_PER_PAGE)


async def confirm_action_unlinkauth(
    ctx: wire.Context, msg: EosActionUnlinkAuth
) -> None:
    text = "Unlink Auth"
    fields = []
    fields.append("Account:")
    fields.append(helpers.eos_name_to_string(msg.account))
    fields.append("Code:")
    fields.append(helpers.eos_name_to_string(msg.code))
    fields.append("Type:")
    fields.append(helpers.eos_name_to_string(msg.type))
    await _require_confirm_paginated(ctx, text, fields, _FOUR_FIELDS_PER_PAGE)


async def confirm_action_newaccount(
    ctx: wire.Context, msg: EosActionNewAccount
) -> None:
    text = "New Account"
    fields = []
    fields.append("Creator:")
    fields.append(helpers.eos_name_to_string(msg.creator))
    fields.append("Name:")
    fields.append(helpers.eos_name_to_string(msg.name))
    fields.extend(authorization_fields(msg.owner))
    fields.extend(authorization_fields(msg.active))
    await _require_confirm_paginated(ctx, text, fields, _FOUR_FIELDS_PER_PAGE)


async def confirm_action_unknown(
    ctx: wire.Context, action: EosActionCommon, checksum: bytes
) -> None:
    text = "Arbitrary data"
    fields = []
    fields.append("Contract:")
    fields.append(helpers.eos_name_to_string(action.account))
    fields.append("Action Name:")
    fields.append(helpers.eos_name_to_string(action.name))
    fields.append("Checksum: ")
    fields.extend(split_data(hexlify(checksum).decode("ascii")))
    await _require_confirm_paginated(ctx, text, fields, _FIVE_FIELDS_PER_PAGE)


def authorization_fields(auth: EosAuthorization) -> List[str]:
    fields = []

    fields.append("Threshold:")
    fields.append(str(auth.threshold))

    for i, key in enumerate(auth.keys):
        _key = helpers.public_key_to_wif(bytes(key.key))
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


def split_data(data: str) -> List[str]:
    lines = []
    while data:
        lines.append("{} ".format(data[:_LINE_LENGTH]))
        data = data[_LINE_LENGTH:]
    return lines
