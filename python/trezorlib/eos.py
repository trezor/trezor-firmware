import binascii
from datetime import datetime
from . import messages as proto
from .tools import CallException, expect, session, b58decode


def int_to_big_endian(value):
    return value.to_bytes((value.bit_length() + 7) // 8, "big")

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

def asset_to_number(asset):
    amount_str, symbol_str = asset.split(' ')
    dot_pos = amount_str.find('.')

    # parse symbol
    if dot_pos != -1:
        precision_digit = len(amount_str) - dot_pos - 1
    else:
        precision_digit = 0

    sym = symbol_from_string(precision_digit, symbol_str)

    # parse amount
    if dot_pos != -1:
        int_part = int(amount_str[:dot_pos])
        fract_part = int(amount_str[dot_pos + 1:])
        if int_part < 0:
            fract_part *= -1
    else:
        int_part = int(amount_str)
        fract_part = 0

    amount = int_part
    amount *= symbol_precision(sym)
    amount += fract_part

    return amount, sym

def char_to_symbol(c):
    if c >= 'a' and c <= 'z':
        return ord(c) - ord('a') + 6
    if c >= '1' and c <= '5':
        return ord(c) - ord('1') + 1
    return 0

def symbol_from_string(p, name):
    length = len(name)
    result = 0
    for i in range(0, length):
        result |= ord(name[i]) << (8 * (i + 1))

    result |= p
    return result

def symbol_precision(sym):
    return pow(10, (sym & 0xff))

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
            proto.EosPermissionLevel(
                actor=name_to_number(auth['actor']),
                permission=name_to_number(auth['permission'])
            )
        )

    return proto.EosActionCommon(
        account=name_to_number(action['account']),
        name=name_to_number(action['name']),
        authorization=authorization
    )

def parse_transfer(data):
    amount, symbol = asset_to_number(data['quantity'])

    return proto.EosActionTransfer(
        sender=name_to_number(data['from']),
        receiver=name_to_number(data['to']),
        memo=data['memo'],
        quantity=proto.EosAsset(
            amount=amount,
            symbol=symbol
        )
    )

def parse_vote_producer(data):
    producers = []
    for producer in data['producers']:
        producers.append(name_to_number(producer))

    return proto.EosActionVoteProducer(
        voter=name_to_number(data['account']),
        proxy=name_to_number(data['proxy']),
        producers=producers
    )

def parse_buy_ram(data):
    amount, symbol = asset_to_number(data['quant'])

    return proto.EosActionBuyRam(
        payer=name_to_number(data['payer']),
        receiver=name_to_number(data['receiver']),
        quantity=proto.EosAsset(
            amount=amount,
            symbol=symbol
        )
    )

def parse_buy_rambytes(data):
    return proto.EosActionBuyRamBytes(
        payer=name_to_number(data['payer']),
        receiver=name_to_number(data['receiver']),
        bytes=int(data['bytes'])
    )

def parse_sell_ram(data):
    return proto.EosActionSellRam(
        account=name_to_number(data['account']),
        bytes=int(data['bytes'])
    )

def parse_delegate(data):
    amount_net, symbol_net = asset_to_number(data['stake_net_quantity'])
    amount_cpu, symbol_cpu = asset_to_number(data['stake_cpu_quantity'])

    return proto.EosActionDelegate(
        sender=name_to_number(data['sender']),
        receiver=name_to_number(data['receiver']),
        net_quantity=proto.EosAsset(
            amount=amount_net,
            symbol=symbol_net
        ),
        cpu_quantity=proto.EosAsset(
            amount=amount_cpu,
            symbol=symbol_cpu
        ),
        transfer=bool(data['transfer'])
    )

def parse_undelegate(data):
    amount_net, symbol_net = asset_to_number(data['unstake_net_quantity'])
    amount_cpu, symbol_cpu = asset_to_number(data['unstake_cpu_quantity'])

    return proto.EosActionUndelegate(
        sender=name_to_number(data['sender']),
        receiver=name_to_number(data['receiver']),
        net_quantity=proto.EosAsset(
            amount=amount_net,
            symbol=symbol_net
        ),
        cpu_quantity=proto.EosAsset(
            amount=amount_cpu,
            symbol=symbol_cpu
        )
    )

def parse_refund(data):
    return proto.EosActionRefund(
        owner=name_to_number(data['owner'])
    )

def parse_updateauth(data):
    auth = parse_authorization(data['auth'])

    return proto.EosActionUpdateAuth(
        account=name_to_number(data['account']),
        permission=name_to_number(data['permission']),
        parent=name_to_number(data['parent']),
        auth=auth
    )

def parse_deleteauth(data):
    return proto.EosActionDeleteAuth(
        account=name_to_number(data['account']),
        permission=name_to_number(data['permission'])
    )

def parse_linkauth(data):
    return proto.EosActionLinkAuth(
        account=name_to_number(data['account']),
        code=name_to_number(data['code']),
        type=name_to_number(data['type']),
        requirement=name_to_number(data['requirement'])
    )

def parse_unlinkauth(data):
    return proto.EosActionUnlinkAuth(
        account=name_to_number(data['account']),
        code=name_to_number(data['code']),
        type=name_to_number(data['type'])
    )

def parse_authorization(data):
    keys = []
    for key in data['keys']:
        _t, _k = public_key_to_buffer(key['key'])

        keys.append(
            proto.EosAuthorizationKey(
                type=_t,
                key=_k,
                address_n=[],
                weight=int(key['weight'])
            )
        )

    accounts = []
    for account in data['accounts']:
        accounts.append(
            proto.EosAuthorizationAccount(
                account=proto.EosPermissionLevel(
                    actor=name_to_number(account['permission']['actor']),
                    permission=name_to_number(account['permission']['permission'])
                ),
                weight=int(account['weight'])
            )
        )

    waits = []
    for wait in data['waits']:
        waits.append(
            proto.EosAuthorizationWait(
                wait_sec=int(wait['wait_sec']),
                weight=int(wait['weight'])
            )
        )

    return proto.EosAuthorization(
        threshold=int(data['threshold']),
        keys=keys,
        accounts=accounts,
        waits=waits,
    )


def parse_new_account(data):
    owner = parse_authorization(data['owner'])
    active = parse_authorization(data['active'])

    return proto.EosActionNewAccount(
        creator=name_to_number(data['creator']),
        name=name_to_number(data['name']),
        owner=owner,
        active=active
    )


def parse_unknown(data):
    return proto.EosActionUnknown(
        data_size=len(binascii.unhexlify(data)),
        data_chunk=binascii.unhexlify(data)
    )

def parse_action(action):
    txAction = proto.EosTxActionAck()
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
    tx.chain_id = binascii.unhexlify(json['chain_id'])

    body = json['transaction']

    expiration = int(datetime.strptime(body['expiration'], '%Y-%m-%dT%H:%M:%S').strftime("%s"))
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

@expect(proto.EosPublicKey)
def get_public_key(client, n, show_display=False, multisig=None):
    response = client.call(proto.EosGetPublicKey(address_n=n, show_display=show_display))
    return response


@session
def sign_tx(client, address, transaction):
    tx = parse_transaction_json(transaction)

    header = proto.EosTxHeader()
    header.expiration = tx.expiration
    header.ref_block_num = tx.ref_block_num
    header.ref_block_prefix = tx.ref_block_prefix
    header.max_net_usage_words = tx.net_usage_words
    header.max_cpu_usage_ms = tx.max_cpu_usage_ms
    header.delay_sec = tx.delay_sec

    msg = proto.EosSignTx()
    msg.address_n = address
    msg.chain_id = tx.chain_id
    msg.header = header
    msg.num_actions = tx.num_actions

    response = client.call(msg)

    try:
        while isinstance(response, proto.EosTxActionRequest):
            response = client.call(parse_action(tx.actions.pop(0)))
    except IndexError:
        # pop from empty list
        raise CallException(
            "Eos.UnexpectedEndOfOperations",
            "Reached end of operations without a signature.",
        ) from None

    if not isinstance(response, proto.EosSignedTx):
        raise CallException(proto.FailureType.UnexpectedMessage, response)

    return response

