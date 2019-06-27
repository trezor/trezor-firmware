from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import chunks, format_amount

from apps.common.confirm import require_confirm


async def require_confirm_data(ctx, data):
    text = Text("Data attached", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.normal(*split_text(data))
    return await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_tx(ctx, dest, value):
    text = Text("Confirm sending", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold(format_amount_trx(value))
    text.mono(*split_address("To: " + dest))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_tx_asset(ctx, token, dest, value, decimals=0):
    text = Text("Confirm sending", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold(format_amount(value, decimals) + token)
    text.mono(*split_address("To: " + dest))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_vote_witness(ctx, votes_addr, votes_total):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("SR Voting")
    text.normal("N. Candidates: {}".format(votes_addr))
    text.normal("Total Votes: {}".format(votes_total))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_witness_contract(ctx, url):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("Apply for SR")
    text.mono(*split_text("URL: {}".format(url)))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_asset_issue(
    ctx, token_name, token_abbr, supply, trx_num, num, precision
):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("Create Token")
    text.normal(token_name)
    text.normal(format_amount(supply, precision) + token_abbr)
    text.mono(
        "Ratio {}:{}".format(format_amount(trx_num, 6), format_amount(num, precision))
    )
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_witness_update(ctx, owner_address, update_url):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("Update Witness")
    text.normal(owner_address)
    text.mono(*split_address("URL: {}".format(update_url)))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_participate_asset(ctx, token, value, decimals):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("Token Participate:")
    text.mono(token)
    text.bold("Amount:")
    text.mono(format_amount(value, decimals))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_account_update(ctx, account_name):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("Account Update")
    text.mono("Name:")
    text.mono(account_name)
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_freeze_balance(ctx, value, days, resource, receiver):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("Freeze Balance")
    text.mono("Amount:")
    text.bold(format_amount_trx(value))
    text.mono("Days: {}".format(days))
    if resource == 1:
        text.mono("to gain energy")
    else:
        text.mono("to gain banwidth")

    try:
        await require_confirm(ctx, text, ButtonRequestType.SignTx)
    except AttributeError:
        return False
    if receiver is not None:
        text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
        text.bold("Freeze Balance")
        text.mono("Assign to: ")
        text.mono(*split_text(receiver))
        return await require_confirm(ctx, text, ButtonRequestType.SignTx)
    else:
        return True


async def require_confirm_unfreeze_balance(ctx, resource, receiver):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("Unfreeze Balance")
    text.mono(
        *split_text(
            "{}{} will be unfreeze.".format(
                "Energy" if resource == 1 else "Bandwidth",
                "" if receiver is None else " assigned to" + receiver,
            )
        )
    )
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_withdraw_balance(ctx):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("Withdraw Balance")
    text.mono(*split_text("Withdraw total allowance  to your account."))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_unfreeze_asset(ctx):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold("Unfreeze Assets")
    text.mono(*split_text("Unfreeze expired frozen assets."))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_update_asset(ctx, description, url):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Update Token")
    text.mono(*split_text(description))
    text.mono(url)
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_proposal_create_contract(ctx, parameters):
    for idx in range(len(parameters)):
        text = Text("Confirm proposal", ui.ICON_CONFIRM, icon_color=ui.GREEN)
        lines = "Parameter: {}".format(get_parameter_text(parameters[idx].key))
        text.normal(*split_text(lines))
        lines = "Value: {}".format(parameters[idx].value)
        text.mono(*split_text(lines))
        try:
            await require_confirm(ctx, text, ButtonRequestType.SignTx)
        except AttributeError:
            return False
    return True


async def require_confirm_proposal_approve_contract(ctx, proposal_id, is_add_approval):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Proposal Approval")
    text.mono("ID: {}".format(proposal_id))
    text.mono("Approve: {}".format(is_add_approval))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_proposal_delete_contract(ctx, proposal_id):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Proposal Delete")
    text.mono("ID: {}".format(proposal_id))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_set_account_id_contract(ctx, account_id):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Set Accoount ID")
    text.mono("ID: {}".format(account_id))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_create_smart_contract(ctx, create_smart_contract):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Create Smart Contract")
    if create_smart_contract.token_id:
        text.mono("Token ID:")
        text.bold("{}".format(create_smart_contract.token_id))
    if create_smart_contract.call_token_value:
        text.mono("Token Amount:")
        text.bold(format_amount(create_smart_contract.call_token_value))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_trigger_smart_contract(
    ctx, contract_address, trigger_smart_contract
):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Trigger Smart Contract")
    text.mono("Contract Address:")
    text.bold(contract_address)
    if trigger_smart_contract.call_value:
        text.mono("TRX Amount:")
        text.bold("{}".format(trigger_smart_contract.call_value))
    if trigger_smart_contract.token_id:
        text.mono("Token ID:")
        text.bold("{}".format(trigger_smart_contract.token_id))
    if trigger_smart_contract.call_token_value:
        text.mono("Token Amount:")
        text.bold(format_amount(trigger_smart_contract.call_token_value))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_update_setting_contract(
    ctx, contract_address, consume_user_resource_percent
):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Update Smart Contract Resource Consumption")
    text.mono("Contract Address:")
    text.bold(contract_address)
    text.mono("Percentage:")
    text.bold("{}%".format(consume_user_resource_percent))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_exchange_create_contract(
    ctx,
    first_token_name: int,
    first_token_balance: int,
    second_token_name: int,
    second_token_balance: int,
):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Create Exchange")
    text.mono("First Token:")
    text.bold(format_amount(first_token_balance) + first_token_name)
    text.mono("Second Token :")
    text.bold(format_amount(second_token_balance) + second_token_name)
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_exchange_inject_contract(
    ctx, exchange_id: int, token_name: int, quantity: int
):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Inject Exchange")
    text.mono("Exchange ID:")
    text.bold(exchange_id)
    text.mono("Token:")
    text.bold(token_name)
    text.mono("Quantity")
    text.bold(quantity)
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_exchange_withdraw_contract(
    ctx, exchange_id: int, token_name: int, quantity: int
):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Withdraw Exchange")
    text.mono("Exchange ID:")
    text.bold(exchange_id)
    text.mono("Token:")
    text.bold(token_name)
    text.mono("Quantity")
    text.bold(quantity)
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_exchange_transaction_contract(
    ctx, exchange_id: int, token_1, token_2, quantity: int, expected: int
):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Exchange Transaction")
    text.mono("Exchange ID:")
    text.bold(exchange_id)
    text.mono("Token:")
    text.bold(format_amount(quantity) + token_1)
    text.mono("Expected")
    text.bold(format_amount(expected) + token_2)
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_update_energy_limit_contract(
    ctx, contract_address, energy_limit
):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Update Energy Limit")
    text.mono("Contract Address:")
    text.bold(contract_address)
    text.mono("Origin Energy Limit")
    text.bold(energy_limit)
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_account_permission_update_contract(ctx):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Account Permission Update")
    # TODO
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_cancel_deferred_transaction_contract(ctx):
    text = Text("Confirm transaction", ui.ICON_CONFIRM, icon_color=ui.GREEN)
    text.bold("Cancel Deferred Transaction")
    # TODO
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


def format_amount_trx(value):
    return "%s TRX" % format_amount(value, 6)


def split_address(address):
    return chunks(address, 16)


def split_text(text):
    return chunks(text, 18)


def get_parameter_text(code):
    parameter = {
        0: "Maintenance time interval",
        1: "Account upgrade cost",
        2: "Create account fee",
        3: "Transaction fee",
        4: "Asset issue fee",
        5: "Witness pay per block",
        6: "Witness standby allowance",
        7: "Create new account fee in system contract",
        8: "Create new account bandwidth rate",
        9: "Allow creation of contracts",
        10: "Remove the power of GRs",
        11: "Energy fee",
        12: "Exchange create fee",
        13: "Max CPU time of one TX",
    }
    return parameter.get(code, "Invalid parameter")
