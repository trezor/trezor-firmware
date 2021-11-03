# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from datetime import datetime

from . import exceptions, messages
from .tools import b58decode, expect, session


def name_to_number(name):
    length = len(name)
    value = 0

    for i in range(0, 13):
        c = 0
        if i < length and i < 13:
            c = char_to_symbol(name[i])

        if i < 12:
            c &= 0x1F
            c <<= 64 - 5 * (i + 1)
        else:
            c &= 0x0F

        value |= c

    return value


def char_to_symbol(c):
    if c >= "a" and c <= "z":
        return ord(c) - ord("a") + 6
    elif c >= "1" and c <= "5":
        return ord(c) - ord("1") + 1
    else:
        return 0


def parse_asset(asset):
    amount_str, symbol_str = asset.split(" ")

    # "-1.0000" => ["-1", "0000"] => -10000
    amount_parts = amount_str.split(".", maxsplit=1)
    amount = int("".join(amount_parts))

    precision = 0
    if len(amount_parts) > 1:
        precision = len(amount_parts[1])

        # 4, "EOS" => b"\x04EOS" => little-endian uint32
    symbol_bytes = bytes([precision]) + symbol_str.encode()
    symbol = int.from_bytes(symbol_bytes, "little")

    return messages.EosAsset(amount=amount, symbol=symbol)


def public_key_to_buffer(pub_key):
    _t = 0
    if pub_key[:3] == "EOS":
        pub_key = pub_key[3:]
        _t = 0
    elif pub_key[:7] == "PUB_K1_":
        pub_key = pub_key[7:]
        _t = 0
    elif pub_key[:7] == "PUB_R1_":
        pub_key = pub_key[7:]
        _t = 1

    return _t, b58decode(pub_key, None)[:-4]


def parse_common(action):
    authorization = []
    for auth in action["authorization"]:
        authorization.append(
            messages.EosPermissionLevel(
                actor=name_to_number(auth["actor"]),
                permission=name_to_number(auth["permission"]),
            )
        )

    return messages.EosActionCommon(
        account=name_to_number(action["account"]),
        name=name_to_number(action["name"]),
        authorization=authorization,
    )


def parse_transfer(data):
    return messages.EosActionTransfer(
        sender=name_to_number(data["from"]),
        receiver=name_to_number(data["to"]),
        memo=data["memo"],
        quantity=parse_asset(data["quantity"]),
    )


def parse_vote_producer(data):
    producers = []
    for producer in data["producers"]:
        producers.append(name_to_number(producer))

    return messages.EosActionVoteProducer(
        voter=name_to_number(data["account"]),
        proxy=name_to_number(data["proxy"]),
        producers=producers,
    )


def parse_buy_ram(data):
    return messages.EosActionBuyRam(
        payer=name_to_number(data["payer"]),
        receiver=name_to_number(data["receiver"]),
        quantity=parse_asset(data["quant"]),
    )


def parse_buy_rambytes(data):
    return messages.EosActionBuyRamBytes(
        payer=name_to_number(data["payer"]),
        receiver=name_to_number(data["receiver"]),
        bytes=int(data["bytes"]),
    )


def parse_sell_ram(data):
    return messages.EosActionSellRam(
        account=name_to_number(data["account"]), bytes=int(data["bytes"])
    )


def parse_delegate(data):
    return messages.EosActionDelegate(
        sender=name_to_number(data["from"]),
        receiver=name_to_number(data["receiver"]),
        net_quantity=parse_asset(data["stake_net_quantity"]),
        cpu_quantity=parse_asset(data["stake_cpu_quantity"]),
        transfer=bool(data["transfer"]),
    )


def parse_undelegate(data):
    return messages.EosActionUndelegate(
        sender=name_to_number(data["from"]),
        receiver=name_to_number(data["receiver"]),
        net_quantity=parse_asset(data["unstake_net_quantity"]),
        cpu_quantity=parse_asset(data["unstake_cpu_quantity"]),
    )


def parse_refund(data):
    return messages.EosActionRefund(owner=name_to_number(data["owner"]))


def parse_updateauth(data):
    auth = parse_authorization(data["auth"])

    return messages.EosActionUpdateAuth(
        account=name_to_number(data["account"]),
        permission=name_to_number(data["permission"]),
        parent=name_to_number(data["parent"]),
        auth=auth,
    )


def parse_deleteauth(data):
    return messages.EosActionDeleteAuth(
        account=name_to_number(data["account"]),
        permission=name_to_number(data["permission"]),
    )


def parse_linkauth(data):
    return messages.EosActionLinkAuth(
        account=name_to_number(data["account"]),
        code=name_to_number(data["code"]),
        type=name_to_number(data["type"]),
        requirement=name_to_number(data["requirement"]),
    )


def parse_unlinkauth(data):
    return messages.EosActionUnlinkAuth(
        account=name_to_number(data["account"]),
        code=name_to_number(data["code"]),
        type=name_to_number(data["type"]),
    )


def parse_authorization(data):
    keys = []
    for key in data["keys"]:
        _t, _k = public_key_to_buffer(key["key"])

        keys.append(
            messages.EosAuthorizationKey(type=_t, key=_k, weight=int(key["weight"]))
        )

    accounts = []
    for account in data["accounts"]:
        accounts.append(
            messages.EosAuthorizationAccount(
                account=messages.EosPermissionLevel(
                    actor=name_to_number(account["permission"]["actor"]),
                    permission=name_to_number(account["permission"]["permission"]),
                ),
                weight=int(account["weight"]),
            )
        )

    waits = []
    for wait in data["waits"]:
        waits.append(
            messages.EosAuthorizationWait(
                wait_sec=int(wait["wait_sec"]), weight=int(wait["weight"])
            )
        )

    return messages.EosAuthorization(
        threshold=int(data["threshold"]), keys=keys, accounts=accounts, waits=waits
    )


def parse_new_account(data):
    owner = parse_authorization(data["owner"])
    active = parse_authorization(data["active"])

    return messages.EosActionNewAccount(
        creator=name_to_number(data["creator"]),
        name=name_to_number(data["name"]),
        owner=owner,
        active=active,
    )


def parse_unknown(data):
    data_bytes = bytes.fromhex(data)
    return messages.EosActionUnknown(data_size=len(data_bytes), data_chunk=data_bytes)


def parse_action(action):
    tx_action = messages.EosTxActionAck(common=parse_common(action))
    data = action["data"]

    if action["account"] == "eosio":
        if action["name"] == "voteproducer":
            tx_action.vote_producer = parse_vote_producer(data)
        elif action["name"] == "buyram":
            tx_action.buy_ram = parse_buy_ram(data)
        elif action["name"] == "buyrambytes":
            tx_action.buy_ram_bytes = parse_buy_rambytes(data)
        elif action["name"] == "sellram":
            tx_action.sell_ram = parse_sell_ram(data)
        elif action["name"] == "delegatebw":
            tx_action.delegate = parse_delegate(data)
        elif action["name"] == "undelegatebw":
            tx_action.undelegate = parse_undelegate(data)
        elif action["name"] == "refund":
            tx_action.refund = parse_refund(data)
        elif action["name"] == "updateauth":
            tx_action.update_auth = parse_updateauth(data)
        elif action["name"] == "deleteauth":
            tx_action.delete_auth = parse_deleteauth(data)
        elif action["name"] == "linkauth":
            tx_action.link_auth = parse_linkauth(data)
        elif action["name"] == "unlinkauth":
            tx_action.unlink_auth = parse_unlinkauth(data)
        elif action["name"] == "newaccount":
            tx_action.new_account = parse_new_account(data)
    elif action["name"] == "transfer":
        tx_action.transfer = parse_transfer(data)
    else:
        tx_action.unknown = parse_unknown(data)

    return tx_action


def parse_transaction_json(transaction):
    header = messages.EosTxHeader(
        expiration=int(
            (
                datetime.strptime(transaction["expiration"], "%Y-%m-%dT%H:%M:%S")
                - datetime(1970, 1, 1)
            ).total_seconds()
        ),
        ref_block_num=int(transaction["ref_block_num"]),
        ref_block_prefix=int(transaction["ref_block_prefix"]),
        max_net_usage_words=int(transaction["max_net_usage_words"]),
        max_cpu_usage_ms=int(transaction["max_cpu_usage_ms"]),
        delay_sec=int(transaction["delay_sec"]),
    )

    actions = [parse_action(a) for a in transaction["actions"]]

    return header, actions


# ====== Client functions ====== #


@expect(messages.EosPublicKey)
def get_public_key(client, n, show_display=False, multisig=None):
    response = client.call(
        messages.EosGetPublicKey(address_n=n, show_display=show_display)
    )
    return response


@session
def sign_tx(client, address, transaction, chain_id):
    header, actions = parse_transaction_json(transaction)

    msg = messages.EosSignTx(
        address_n=address,
        chain_id=bytes.fromhex(chain_id),
        header=header,
        num_actions=len(actions),
    )

    response = client.call(msg)

    try:
        while isinstance(response, messages.EosTxActionRequest):
            response = client.call(actions.pop(0))
    except IndexError:
        # pop from empty list
        raise exceptions.TrezorException(
            "Reached end of operations without a signature."
        ) from None

    if not isinstance(response, messages.EosSignedTx):
        raise exceptions.TrezorException(
            f"Unexpected message: {response.__class__.__name__}"
        )

    return response
