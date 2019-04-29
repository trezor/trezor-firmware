from datetime import datetime
from . import messages
from .tools import CallException, expect, session, b58decode


def name_to_number(name):
    length = len(name)
    value = 0

    for i in range(0, 13):
        c = 0
        if i < length and i < 13:
            c = char_to_symbol(name[i])

        if i < 12:
            c &= 0x1f
            c <<= 64 - 5 * (i + 1)
        else:
            c &= 0x0f

        value |= c

    return value


def char_to_symbol(c):
    if c >= 'a' and c <= 'z':
        return ord(c) - ord('a') + 6
    elif c >= '1' and c <= '5':
        return ord(c) - ord('1') + 1
    else:
        return 0


def parse_asset(asset):
    amount_str, symbol_str = asset.split(' ')

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
    if pub_key[:3] == 'EOS':
        pub_key = pub_key[3:]
        _t = 0
    elif pub_key[:7] == 'PUB_K1_':
        pub_key = pub_key[7:]
        _t = 0
    elif pub_key[:7] == 'PUB_R1_':
        pub_key = pub_key[7:]
        _t = 1

    return _t, b58decode(pub_key, None)[:-4]


def parse_common(action):
    authorization = []
    for auth in action['authorization']:
        authorization.append(
            messages.EosPermissionLevel(
                actor=name_to_number(auth['actor']),
                permission=name_to_number(auth['permission'])
            )
        )

    return messages.EosActionCommon(
        account=name_to_number(action['account']),
        name=name_to_number(action['name']),
        authorization=authorization
    )


def parse_transfer(data):
    return messages.EosActionTransfer(
        sender=name_to_number(data['from']),
        receiver=name_to_number(data['to']),
        memo=data['memo'],
        quantity=parse_asset(data['quantity'])
    )


def parse_vote_producer(data):
    producers = []
    for producer in data['producers']:
        producers.append(name_to_number(producer))

    return messages.EosActionVoteProducer(
        voter=name_to_number(data['account']),
        proxy=name_to_number(data['proxy']),
        producers=producers
    )


def parse_buy_ram(data):
    return messages.EosActionBuyRam(
        payer=name_to_number(data['payer']),
        receiver=name_to_number(data['receiver']),
        quantity=parse_asset(data['quant'])
    )


def parse_buy_rambytes(data):
    return messages.EosActionBuyRamBytes(
        payer=name_to_number(data['payer']),
        receiver=name_to_number(data['receiver']),
        bytes=int(data['bytes'])
    )


def parse_sell_ram(data):
    return messages.EosActionSellRam(
        account=name_to_number(data['account']),
        bytes=int(data['bytes'])
    )


def parse_delegate(data):
    return messages.EosActionDelegate(
        sender=name_to_number(data['sender']),
        receiver=name_to_number(data['receiver']),
        net_quantity=parse_asset(data['stake_net_quantity']),
        cpu_quantity=parse_asset(data['stake_cpu_quantity']),
        transfer=bool(data['transfer'])
    )


def parse_undelegate(data):
    return messages.EosActionUndelegate(
        sender=name_to_number(data['sender']),
        receiver=name_to_number(data['receiver']),
        net_quantity=parse_asset(data['unstake_net_quantity']),
        cpu_quantity=parse_asset(data['unstake_cpu_quantity'])
    )


def parse_refund(data):
    return messages.EosActionRefund(
        owner=name_to_number(data['owner'])
    )


def parse_updateauth(data):
    auth = parse_authorization(data['auth'])

    return messages.EosActionUpdateAuth(
        account=name_to_number(data['account']),
        permission=name_to_number(data['permission']),
        parent=name_to_number(data['parent']),
        auth=auth
    )


def parse_deleteauth(data):
    return messages.EosActionDeleteAuth(
        account=name_to_number(data['account']),
        permission=name_to_number(data['permission'])
    )


def parse_linkauth(data):
    return messages.EosActionLinkAuth(
        account=name_to_number(data['account']),
        code=name_to_number(data['code']),
        type=name_to_number(data['type']),
        requirement=name_to_number(data['requirement'])
    )


def parse_unlinkauth(data):
    return messages.EosActionUnlinkAuth(
        account=name_to_number(data['account']),
        code=name_to_number(data['code']),
        type=name_to_number(data['type'])
    )


def parse_authorization(data):
    keys = []
    for key in data['keys']:
        _t, _k = public_key_to_buffer(key['key'])

        keys.append(
            messages.EosAuthorizationKey(
                type=_t,
                key=_k,
                address_n=[],
                weight=int(key['weight'])
            )
        )

    accounts = []
    for account in data['accounts']:
        accounts.append(
            messages.EosAuthorizationAccount(
                account=messages.EosPermissionLevel(
                    actor=name_to_number(account['permission']['actor']),
                    permission=name_to_number(account['permission']['permission'])
                ),
                weight=int(account['weight'])
            )
        )

    waits = []
    for wait in data['waits']:
        waits.append(
            messages.EosAuthorizationWait(
                wait_sec=int(wait['wait_sec']),
                weight=int(wait['weight'])
            )
        )

    return messages.EosAuthorization(
        threshold=int(data['threshold']),
        keys=keys,
        accounts=accounts,
        waits=waits,
    )


def parse_new_account(data):
    owner = parse_authorization(data['owner'])
    active = parse_authorization(data['active'])

    return messages.EosActionNewAccount(
        creator=name_to_number(data['creator']),
        name=name_to_number(data['name']),
        owner=owner,
        active=active
    )


def parse_unknown(data):
    data_bytes = bytes.fromhex(data)
    return messages.EosActionUnknown(
        data_size=len(data_bytes),
        data_chunk=data_bytes
    )


def parse_action(action):
    txAction = messages.EosTxActionAck()
    data = action['data']

    txAction.common = parse_common(action)

    if action['account'] == 'eosio':
        if action['name'] == 'voteproducer':
            txAction.vote_producer = parse_vote_producer(data)
        elif action['name'] == 'buyram':
            txAction.buy_ram = parse_buy_ram(data)
        elif action['name'] == 'buyrambytes':
            txAction.buy_ram_bytes = parse_buy_rambytes(data)
        elif action['name'] == 'sellram':
            txAction.sell_ram = parse_sell_ram(data)
        elif action['name'] == 'delegatebw':
            txAction.delegate = parse_delegate(data)
        elif action['name'] == 'undelegatebw':
            txAction.undelegate = parse_undelegate(data)
        elif action['name'] == 'refund':
            txAction.refund = parse_refund(data)
        elif action['name'] == 'updateauth':
            txAction.update_auth = parse_updateauth(data)
        elif action['name'] == 'deleteauth':
            txAction.delete_auth = parse_deleteauth(data)
        elif action['name'] == 'linkauth':
            txAction.link_auth = parse_linkauth(data)
        elif action['name'] == 'unlinkauth':
            txAction.unlink_auth = parse_unlinkauth(data)
        elif action['name'] == 'newaccount':
            txAction.new_account = parse_new_account(data)
    elif action['name'] == 'transfer':
        txAction.transfer = parse_transfer(data)
    else:
        txAction.unknown = parse_unknown(data)

    return txAction


def parse_transaction_json(json):
    tx = type('Transaction', (object,), {})()
    tx.chain_id = bytes.fromhex(json['chain_id'])

    body = json['transaction']
  
    expiration = int((datetime.strptime(body['expiration'], '%Y-%m-%dT%H:%M:%S') - datetime(1970, 1, 1)).total_seconds())
    tx.expiration = expiration
    tx.ref_block_num = int(body['ref_block_num'])
    tx.ref_block_prefix = int(body['ref_block_prefix'])
    tx.net_usage_words = int(body['net_usage_words'])
    tx.max_cpu_usage_ms = int(body['max_cpu_usage_ms'])
    tx.delay_sec = int(body['delay_sec'])

    tx.actions = body['actions']

    tx.num_actions = len(tx.actions)

    return tx

# ====== Client functions ====== #


@expect(messages.EosPublicKey)
def get_public_key(client, n, show_display=False, multisig=None):
    response = client.call(messages.EosGetPublicKey(address_n=n, show_display=show_display))
    return response


@session
def sign_tx(client, address, transaction):
    tx = parse_transaction_json(transaction)

    header = messages.EosTxHeader()
    header.expiration = tx.expiration
    header.ref_block_num = tx.ref_block_num
    header.ref_block_prefix = tx.ref_block_prefix
    header.max_net_usage_words = tx.net_usage_words
    header.max_cpu_usage_ms = tx.max_cpu_usage_ms
    header.delay_sec = tx.delay_sec

    msg = messages.EosSignTx()
    msg.address_n = address
    msg.chain_id = tx.chain_id
    msg.header = header
    msg.num_actions = tx.num_actions

    response = client.call(msg)

    try:
        while isinstance(response, messages.EosTxActionRequest):
            response = client.call(parse_action(tx.actions.pop(0)))
    except IndexError:
        # pop from empty list
        raise CallException(
            "Eos.UnexpectedEndOfOperations",
            "Reached end of operations without a signature.",
        ) from None

    if not isinstance(response, messages.EosSignedTx):
        raise CallException(messages.FailureType.UnexpectedMessage, response)

    return response
