from trezor import ui, wire
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_properties

from .. import helpers

if False:
    from trezor.wire import Context
    from trezor.messages import (
        EosActionBuyRam,
        EosActionBuyRamBytes,
        EosActionCommon,
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
        EosAuthorization,
    )
    from trezor.ui.layouts import PropertyType


async def confirm_action_buyram(ctx: Context, msg: EosActionBuyRam) -> None:
    await confirm_properties(
        ctx,
        "confirm_buyram",
        title="Buy RAM",
        props=[
            ("Payer:", helpers.eos_name_to_string(msg.payer)),
            ("Receiver:", helpers.eos_name_to_string(msg.receiver)),
            ("Amount:", helpers.eos_asset_to_string(msg.quantity)),
        ],
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_buyrambytes(ctx: Context, msg: EosActionBuyRamBytes) -> None:
    await confirm_properties(
        ctx,
        "confirm_buyrambytes",
        title="Buy RAM",
        props=[
            ("Payer:", helpers.eos_name_to_string(msg.payer)),
            ("Receiver:", helpers.eos_name_to_string(msg.receiver)),
            ("Bytes:", str(msg.bytes)),
        ],
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_delegate(ctx: Context, msg: EosActionDelegate) -> None:
    props = [
        ("Sender:", helpers.eos_name_to_string(msg.sender)),
        ("Receiver:", helpers.eos_name_to_string(msg.receiver)),
        ("CPU:", helpers.eos_asset_to_string(msg.cpu_quantity)),
        ("NET:", helpers.eos_asset_to_string(msg.net_quantity)),
    ]
    if msg.transfer:
        props.append(("Transfer:", "Yes"))
        props.append(("Receiver:", helpers.eos_name_to_string(msg.receiver)))
    else:
        props.append(("Transfer:", "No"))

    await confirm_properties(
        ctx,
        "confirm_delegate",
        title="Delegate",
        props=props,
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_sellram(ctx: Context, msg: EosActionSellRam) -> None:
    await confirm_properties(
        ctx,
        "confirm_sellram",
        title="Sell RAM",
        props=[
            ("Receiver:", helpers.eos_name_to_string(msg.account)),
            ("Bytes:", str(msg.bytes)),
        ],
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_undelegate(ctx: Context, msg: EosActionUndelegate) -> None:
    await confirm_properties(
        ctx,
        "confirm_undelegate",
        title="Undelegate",
        props=[
            ("Sender:", helpers.eos_name_to_string(msg.sender)),
            ("Receiver:", helpers.eos_name_to_string(msg.receiver)),
            ("CPU:", helpers.eos_asset_to_string(msg.cpu_quantity)),
            ("NET:", helpers.eos_asset_to_string(msg.net_quantity)),
        ],
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_refund(ctx: Context, msg: EosActionRefund) -> None:
    await confirm_properties(
        ctx,
        "confirm_refund",
        title="Refund",
        props=[
            ("Owner:", helpers.eos_name_to_string(msg.owner)),
        ],
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_voteproducer(ctx: Context, msg: EosActionVoteProducer) -> None:
    if msg.proxy and not msg.producers:
        # PROXY
        await confirm_properties(
            ctx,
            "confirm_voteproducer",
            title="Vote for proxy",
            props=[
                ("Voter:", helpers.eos_name_to_string(msg.voter)),
                ("Proxy:", helpers.eos_name_to_string(msg.proxy)),
            ],
            icon=ui.ICON_CONFIRM,
            br_code=ButtonRequestType.ConfirmOutput,
        )

    elif msg.producers:
        # PRODUCERS
        await confirm_properties(
            ctx,
            "confirm_voteproducer",
            title="Vote for producers",
            props=(
                (f"{wi:2d}. {helpers.eos_name_to_string(producer)}", None)
                for wi, producer in enumerate(msg.producers, 1)
            ),
            icon=ui.ICON_CONFIRM,
            br_code=ButtonRequestType.ConfirmOutput,
        )

    else:
        # Cancel vote
        await confirm_properties(
            ctx,
            "confirm_voteproducer",
            title="Cancel vote",
            props=[
                ("Voter:", helpers.eos_name_to_string(msg.voter)),
            ],
            icon=ui.ICON_CONFIRM,
            br_code=ButtonRequestType.ConfirmOutput,
        )


async def confirm_action_transfer(
    ctx: Context, msg: EosActionTransfer, account: str
) -> None:
    props = [
        ("From:", helpers.eos_name_to_string(msg.sender)),
        ("To:", helpers.eos_name_to_string(msg.receiver)),
        ("Amount:", helpers.eos_asset_to_string(msg.quantity)),
        ("Contract:", account),
    ]
    if msg.memo is not None:
        props.append(("Memo", msg.memo[:512]))
    await confirm_properties(
        ctx,
        "confirm_transfer",
        title="Transfer",
        props=props,
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_updateauth(ctx: Context, msg: EosActionUpdateAuth) -> None:
    props: list[PropertyType] = [
        ("Account:", helpers.eos_name_to_string(msg.account)),
        ("Permission:", helpers.eos_name_to_string(msg.permission)),
        ("Parent:", helpers.eos_name_to_string(msg.parent)),
    ]
    props.extend(authorization_fields(msg.auth))
    await confirm_properties(
        ctx,
        "confirm_updateauth",
        title="Update Auth",
        props=props,
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_deleteauth(ctx: Context, msg: EosActionDeleteAuth) -> None:
    await confirm_properties(
        ctx,
        "confirm_deleteauth",
        title="Delete Auth",
        props=[
            ("Account:", helpers.eos_name_to_string(msg.account)),
            ("Permission:", helpers.eos_name_to_string(msg.permission)),
        ],
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_linkauth(ctx: Context, msg: EosActionLinkAuth) -> None:
    await confirm_properties(
        ctx,
        "confirm_linkauth",
        title="Link Auth",
        props=[
            ("Account:", helpers.eos_name_to_string(msg.account)),
            ("Code:", helpers.eos_name_to_string(msg.code)),
            ("Type:", helpers.eos_name_to_string(msg.type)),
            ("Requirement:", helpers.eos_name_to_string(msg.requirement)),
        ],
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_unlinkauth(ctx: Context, msg: EosActionUnlinkAuth) -> None:
    await confirm_properties(
        ctx,
        "confirm_unlinkauth",
        title="Unlink Auth",
        props=[
            ("Account:", helpers.eos_name_to_string(msg.account)),
            ("Code:", helpers.eos_name_to_string(msg.code)),
            ("Type:", helpers.eos_name_to_string(msg.type)),
        ],
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_newaccount(ctx: Context, msg: EosActionNewAccount) -> None:
    props: list[PropertyType] = [
        ("Creator:", helpers.eos_name_to_string(msg.creator)),
        ("Name:", helpers.eos_name_to_string(msg.name)),
    ]
    props.extend(authorization_fields(msg.owner))
    props.extend(authorization_fields(msg.active))
    await confirm_properties(
        ctx,
        "confirm_newaccount",
        title="New Account",
        props=props,
        icon=ui.ICON_CONFIRM,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_unknown(
    ctx: Context, action: EosActionCommon, checksum: bytes
) -> None:
    await confirm_properties(
        ctx,
        "confirm_unknown",
        title="Arbitrary data",
        props=[
            ("Contract:", helpers.eos_name_to_string(action.account)),
            ("Action Name:", helpers.eos_name_to_string(action.name)),
            ("Checksum:", checksum),
        ],
        icon=ui.ICON_WIPE,
        icon_color=ui.RED,
        br_code=ButtonRequestType.ConfirmOutput,
    )


def authorization_fields(auth: EosAuthorization) -> list[PropertyType]:
    fields: list[PropertyType] = []
    fields.append(("Threshold:", str(auth.threshold)))

    for i, key in enumerate(auth.keys, 1):
        if key.key is None:
            raise wire.DataError("Key must be provided explicitly.")

        _key = helpers.public_key_to_wif(bytes(key.key))
        _weight = str(key.weight)

        header = f"Key #{i}:"
        w_header = f"Key #{i} Weight:"

        fields.append((header, _key))
        fields.append((w_header, _weight))

    for i, account in enumerate(auth.accounts, 1):
        _account = helpers.eos_name_to_string(account.account.actor)
        _permission = helpers.eos_name_to_string(account.account.permission)

        a_header = f"Account #{i}:"
        p_header = f"Acc Permission #{i}:"
        w_header = f"Account #{i} weight:"

        fields.append((a_header, _account))
        fields.append((p_header, _permission))
        fields.append((w_header, str(account.weight)))

    for i, wait in enumerate(auth.waits, 1):
        _wait = str(wait.wait_sec)
        _weight = str(wait.weight)

        header = f"Delay #{i}"
        w_header = f"Delay #{i} weight:"
        fields.append((header, f"{_wait} sec"))
        fields.append((w_header, _weight))

    return fields
