import binascii

from . import messages as proto
from .tools import field, expect, CallException, normalize_nfc


@field('address')
@expect(proto.LiskAddress)
def get_address(client, n, show_display=False):
    n = client._convert_prime(n)
    return client.call(proto.LiskGetAddress(address_n=n, show_display=show_display))


@expect(proto.LiskPublicKey)
def get_public_key(client, n, show_display=False):
    n = client._convert_prime(n)
    return client.call(proto.LiskGetPublicKey(address_n=n, show_display=show_display))


@expect(proto.LiskMessageSignature)
def sign_message(client, n, message):
    n = client._convert_prime(n)
    message = normalize_nfc(message)
    return client.call(proto.LiskSignMessage(address_n=n, message=message))


def verify_message(client, pubkey, signature, message):
    message = normalize_nfc(message)
    try:
        resp = client.call(proto.LiskVerifyMessage(signature=signature, public_key=pubkey, message=message))
    except CallException as e:
        resp = e
    return isinstance(resp, proto.Success)


def _asset_to_proto(asset):
    msg = proto.LiskTransactionAsset()

    if "votes" in asset:
        msg.votes = asset["votes"]
    if "data" in asset:
        msg.data = asset["data"]
    if "signature" in asset:
        msg.signature = proto.LiskSignatureType()
        msg.signature.public_key = binascii.unhexlify(asset["signature"]["publicKey"])
    if "delegate" in asset:
        msg.delegate = proto.LiskDelegateType()
        msg.delegate.username = asset["delegate"]["username"]
    if "multisignature" in asset:
        msg.multisignature = proto.LiskMultisignatureType()
        msg.multisignature.min = asset["multisignature"]["min"]
        msg.multisignature.life_time = asset["multisignature"]["lifetime"]
        msg.multisignature.keys_group = asset["multisignature"]["keysgroup"]
    return msg


@expect(proto.LiskSignedTx)
def sign_tx(client, n, transaction):
    n = client._convert_prime(n)

    msg = proto.LiskTransactionCommon()

    msg.type = transaction["type"]
    msg.fee = int(transaction["fee"])  # Lisk use strings for big numbers (javascript issue)
    msg.amount = int(transaction["amount"])  # And we convert it back to number
    msg.timestamp = transaction["timestamp"]

    if "recipientId" in transaction:
        msg.recipient_id = transaction["recipientId"]
    if "senderPublicKey" in transaction:
        msg.sender_public_key = binascii.unhexlify(transaction["senderPublicKey"])
    if "requesterPublicKey" in transaction:
        msg.requester_public_key = binascii.unhexlify(transaction["requesterPublicKey"])
    if "signature" in transaction:
        msg.signature = binascii.unhexlify(transaction["signature"])

    msg.asset = _asset_to_proto(transaction["asset"])
    return client.call(proto.LiskSignTx(address_n=n, transaction=msg))
