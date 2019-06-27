# Serialize TRON Format
from trezor.crypto import base58
from trezor.messages.TronSignTx import TronSignTx

from apps.common.writers import write_bytes

# PROTOBUF3 types
TYPE_VARINT = 0
TYPE_DOUBLE = 1
TYPE_STRING = 2
TYPE_GROUPS = 3
TYPE_GROUPE = 4
TYPE_FLOAT = 5


def add_field(w, fnumber, ftype):
    if fnumber > 15:
        w.append(fnumber << 3 | ftype)
        w.append(0x01)
    else:
        w.append(fnumber << 3 | ftype)


def write_varint(w, value):
    """
    Implements Base 128 variant
    See: https://developers.google.com/protocol-buffers/docs/encoding#varints
    """
    while True:
        byte = value & 0x7F
        value = value >> 7
        if value == 0:
            w.append(byte)
            break
        else:
            w.append(byte | 0x80)


def write_bytes_with_length(w, buf: bytearray):
    write_varint(w, len(buf))
    write_bytes(w, buf)


def pack_contract(contract, owner_address):
    """
    Pack Tron Proto3 Contract
    See: https://github.com/tronprotocol/protocol/blob/master/core/Tron.proto
    and https://github.com/tronprotocol/protocol/blob/master/core/Contract.proto
    """
    retc = bytearray()
    add_field(retc, 1, TYPE_VARINT)
    # contract message
    cmessage = bytearray()
    if contract.transfer_contract:
        write_varint(retc, 1)
        api = "TransferContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(
            cmessage, base58.decode_check(contract.transfer_contract.to_address)
        )
        add_field(cmessage, 3, TYPE_VARINT)
        write_varint(cmessage, contract.transfer_contract.amount)

    if contract.transfer_asset_contract:
        write_varint(retc, 2)
        api = "TransferAssetContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.transfer_asset_contract.asset_id)
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 3, TYPE_STRING)
        write_bytes_with_length(
            cmessage, base58.decode_check(contract.transfer_asset_contract.to_address)
        )
        add_field(cmessage, 4, TYPE_VARINT)
        write_varint(cmessage, contract.transfer_asset_contract.amount)

    if contract.vote_witness_contract:
        write_varint(retc, 4)
        api = "VoteWitnessContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))

        # vote list
        for i in range(len(contract.vote_witness_contract.votes)):
            vote = bytearray()
            add_field(vote, 1, TYPE_STRING)
            write_bytes_with_length(
                vote,
                base58.decode_check(
                    contract.vote_witness_contract.votes[i].vote_address
                ),
            )
            add_field(vote, 2, TYPE_VARINT)
            write_varint(vote, contract.vote_witness_contract.votes[i].vote_count)
            # add to buffer
            add_field(cmessage, 2, TYPE_STRING)
            write_bytes_with_length(cmessage, vote)

    if contract.witness_create_contract:
        write_varint(retc, 5)
        api = "WitnessCreateContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.witness_create_contract.url)

    if contract.asset_issue_contract:
        write_varint(retc, 6)
        api = "AssetIssueContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.asset_issue_contract.name)
        add_field(cmessage, 3, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.asset_issue_contract.abbr)
        add_field(cmessage, 4, TYPE_VARINT)
        write_varint(cmessage, contract.asset_issue_contract.total_supply)
        # asset frozen list
        for i in range(len(contract.asset_issue_contract.frozen_supply)):
            listarr = bytearray()
            add_field(listarr, 1, TYPE_VARINT)
            write_varint(
                listarr, contract.asset_issue_contract.frozen_supply[i].frozen_amount
            )
            add_field(listarr, 2, TYPE_VARINT)
            write_varint(
                listarr, contract.asset_issue_contract.frozen_supply[i].frozen_days
            )
            # add to vote list
            add_field(cmessage, 5, TYPE_STRING)
            write_bytes_with_length(cmessage, listarr)

        add_field(cmessage, 6, TYPE_VARINT)
        write_varint(cmessage, contract.asset_issue_contract.trx_num)
        add_field(cmessage, 7, TYPE_VARINT)
        write_varint(cmessage, contract.asset_issue_contract.precision)
        add_field(cmessage, 8, TYPE_VARINT)
        write_varint(cmessage, contract.asset_issue_contract.num)
        add_field(cmessage, 9, TYPE_VARINT)
        write_varint(cmessage, contract.asset_issue_contract.start_time)
        add_field(cmessage, 10, TYPE_VARINT)
        write_varint(cmessage, contract.asset_issue_contract.end_time)
        add_field(cmessage, 20, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.asset_issue_contract.description)
        add_field(cmessage, 21, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.asset_issue_contract.url)

    if contract.witness_update_contract:
        write_varint(retc, 8)
        api = "WitnessUpdateContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 12, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.witness_update_contract.update_url)

    if contract.participate_asset_issue_contract:
        write_varint(retc, 9)
        api = "ParticipateAssetIssueContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(
            cmessage,
            base58.decode_check(contract.participate_asset_issue_contract.to_address),
        )
        add_field(cmessage, 3, TYPE_STRING)
        write_bytes_with_length(
            cmessage, contract.participate_asset_issue_contract.asset_id
        )
        add_field(cmessage, 4, TYPE_VARINT)
        write_varint(cmessage, contract.participate_asset_issue_contract.amount)

    if contract.account_update_contract:
        write_varint(retc, 10)
        api = "AccountUpdateContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.account_update_contract.account_name)
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))

    if contract.freeze_balance_contract:
        write_varint(retc, 11)
        api = "FreezeBalanceContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_VARINT)
        write_varint(cmessage, contract.freeze_balance_contract.frozen_balance)
        add_field(cmessage, 3, TYPE_VARINT)
        write_varint(cmessage, contract.freeze_balance_contract.frozen_duration)
        if contract.freeze_balance_contract.resource is not None:
            add_field(cmessage, 10, TYPE_VARINT)
            write_varint(cmessage, contract.freeze_balance_contract.resource)
        if contract.freeze_balance_contract.receiver_address is not None:
            add_field(cmessage, 15, TYPE_STRING)
            write_bytes_with_length(
                cmessage,
                base58.decode_check(contract.freeze_balance_contract.receiver_address),
            )

    if contract.unfreeze_balance_contract:
        write_varint(retc, 12)
        api = "UnfreezeBalanceContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))

        if contract.unfreeze_balance_contract.resource is not None:
            add_field(cmessage, 10, TYPE_VARINT)
            write_varint(cmessage, contract.unfreeze_balance_contract.resource)
        if contract.unfreeze_balance_contract.receiver_address is not None:
            add_field(cmessage, 15, TYPE_STRING)
            write_bytes_with_length(
                cmessage,
                base58.decode_check(
                    contract.unfreeze_balance_contract.receiver_address
                ),
            )

    if contract.withdraw_balance_contract:
        write_varint(retc, 13)
        api = "WithdrawBalanceContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))

    if contract.unfreeze_asset_contract:
        write_varint(retc, 14)
        api = "UnfreezeAssetContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))

    if contract.update_asset_contract:
        write_varint(retc, 15)
        api = "UpdateAssetContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.update_asset_contract.description)
        add_field(cmessage, 3, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.update_asset_contract.url)

    if contract.proposal_create_contract:
        write_varint(retc, 16)
        api = "ProposalCreateContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))

        # Parameters list
        for i in range(len(contract.proposal_create_contract.parameters)):
            pair = bytearray()
            add_field(pair, 1, TYPE_VARINT)
            write_varint(pair, contract.proposal_create_contract.parameters[i].key)
            add_field(pair, 2, TYPE_VARINT)
            write_varint(pair, contract.proposal_create_contract.parameters[i].value)
            # add to buffer
            add_field(cmessage, 2, TYPE_STRING)
            write_bytes_with_length(cmessage, pair)

    if contract.proposal_approve_contract:
        write_varint(retc, 17)
        api = "ProposalApproveContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_VARINT)
        write_varint(cmessage, contract.proposal_approve_contract.proposal_id)
        add_field(cmessage, 3, TYPE_VARINT)
        write_varint(cmessage, contract.proposal_approve_contract.is_add_approval)

    if contract.proposal_delete_contract:
        write_varint(retc, 18)
        api = "ProposalDeleteContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_VARINT)
        write_varint(cmessage, contract.proposal_delete_contract.proposal_id)

    if contract.set_account_id:
        write_varint(retc, 19)
        api = "SetAccountIdContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.set_account_id.account_id)
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))

    if contract.exchange_create_contract:
        write_varint(retc, 41)
        api = "ExchangeCreateContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(
            cmessage, contract.exchange_create_contract.first_asset_id
        )
        add_field(cmessage, 3, TYPE_VARINT)
        write_varint(cmessage, contract.exchange_create_contract.first_asset_balance)
        add_field(cmessage, 4, TYPE_STRING)
        write_bytes_with_length(
            cmessage, contract.exchange_create_contract.second_asset_id
        )
        add_field(cmessage, 5, TYPE_VARINT)
        write_varint(cmessage, contract.exchange_create_contract.second_asset_balance)

    if contract.exchange_inject_contract:
        write_varint(retc, 41)
        api = "ExchangeInjectContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.exchange_inject_contract.exchange_id)
        add_field(cmessage, 3, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.exchange_inject_contract.token_id)
        add_field(cmessage, 4, TYPE_VARINT)
        write_varint(cmessage, contract.exchange_inject_contract.quant)

    if contract.exchange_withdraw_contract:
        write_varint(retc, 41)
        api = "ExchangeWithdrawContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(
            cmessage, contract.exchange_withdraw_contract.exchange_id
        )
        add_field(cmessage, 3, TYPE_STRING)
        write_bytes_with_length(cmessage, contract.exchange_withdraw_contract.token_id)
        add_field(cmessage, 4, TYPE_VARINT)
        write_varint(cmessage, contract.exchange_withdraw_contract.quant)

    if contract.exchange_transaction_contract:
        write_varint(retc, 41)
        api = "ExchangeTransactionContract"

        add_field(cmessage, 1, TYPE_STRING)
        write_bytes_with_length(cmessage, base58.decode_check(owner_address))
        add_field(cmessage, 2, TYPE_STRING)
        write_bytes_with_length(
            cmessage, contract.exchange_transaction_contract.exchange_id
        )
        add_field(cmessage, 3, TYPE_STRING)
        write_bytes_with_length(
            cmessage, contract.exchange_transaction_contract.token_id
        )
        add_field(cmessage, 4, TYPE_VARINT)
        write_varint(cmessage, contract.exchange_transaction_contract.quant)
        add_field(cmessage, 5, TYPE_VARINT)
        write_varint(cmessage, contract.exchange_transaction_contract.expected)

    # write API
    capi = bytearray()
    add_field(capi, 1, TYPE_STRING)
    write_bytes_with_length(capi, "type.googleapis.com/protocol." + api)

    # extend to capi
    add_field(capi, 2, TYPE_STRING)
    write_bytes_with_length(capi, cmessage)

    # extend to contract
    add_field(retc, 2, TYPE_STRING)
    write_bytes_with_length(retc, capi)
    return retc


def serialize(transaction: TronSignTx, owner_address: str):
    # transaction parameters
    ret = bytearray()

    add_field(ret, 1, TYPE_STRING)
    write_bytes_with_length(ret, transaction.ref_block_bytes)
    add_field(ret, 4, TYPE_STRING)
    write_bytes_with_length(ret, transaction.ref_block_hash)
    add_field(ret, 8, TYPE_VARINT)
    write_varint(ret, transaction.expiration)
    if transaction.data is not None:
        add_field(ret, 10, TYPE_STRING)
        write_bytes_with_length(ret, transaction.data)

    # add Contract
    retc = pack_contract(transaction.contract, owner_address)

    add_field(ret, 11, TYPE_STRING)
    write_bytes_with_length(ret, retc)
    # add timestamp
    add_field(ret, 14, TYPE_VARINT)
    write_varint(ret, transaction.timestamp)

    return ret
