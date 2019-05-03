# Binance format serializer
#
# Encoding Documentation:
# https://binance-chain.github.io/encoding.html#binance-chain-transaction-encoding-specification
# 

from micropython import const

from . import helpers

STD_SIGNATURE_PREFIX = const(0xEB5AE987)
PUBKEY_PREFIX = const(0xEB5AE987)
SEND_MSG_PREFIX = const(0x2A2C87FA)
NEW_ORDER_MSG_PREFIX = const(0xCE6DC043)
CANCEL_ORDER_MSG_PREFIX = const(0x166E681B)
FREEZE_TOKEN_MSG_PREFIX = const(0xE774B32D)
UNFREEZE_TOKEN_MSG_PREFIX = const(0x6515FF0D)
VOTE_MSG_PREFIX = const(0xA1CADD36)


_ENVELOPE_BLUEPRINT = '{{"account_number":"{account_number}","chain_id":"{chain_id}","memo":"{memo}","msgs":[{msgs}],"sequence":"{sequence}"}}'
_MSG_TRANSFER_BLUEPRINT = '{{"inputs":[{{"address":"{input_address}","coins":[{{"amount":{input_amount},"denom":"{input_denom}"}}]}}],"outputs":[{{"address":"{output_address}","coins":[{{"amount":{output_amount},"denom":"{output_denom}"}}]}}]}}'
_MSG_NEWORDER_BLUEPRINT = '{{"id":"{id}","ordertype":{ordertype},"price":{price},"quantity":{quantity},"sender":"{sender}","side":{side},"symbol":"{symbol}","timeinforce":{timeinforce}}}'
_MSG_CANCEL_BLUEPRINT = '{{"refid":"{refid}","sender":"{sender}","symbol":"{symbol}}}'



def produce_json_for_signing() -> str:
    msg = _MSG_NEWORDER_BLUEPRINT.format(id="B6561DCC104130059A7C08F48C64610C1F6F9064-10", ordertype=2, price=100000000,
                                        quantity=1200000000, sender="bnc1ketpmnqsgycqtxnupr6gcerpps0klyryhz6fzl", side=1,
                                        symbol="BTC-5C4_BNB", timeinforce=1)

    return _ENVELOPE_BLUEPRINT.format(account_number="1", chain_id="bnbchain-1000", memo="", msgs=msg, sequence="9")


# TODO: calculate varint of size of encoded bytes
def calculate_size(value: bytes) -> int:
    return 0
