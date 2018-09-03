
from . import messages as proto
from .protobuf import dict_to_proto
from .tools import CallException, dict_from_camelcase, expect, normalize_nfc


@expect(proto.LiskAddress, field="address")
def get_address(client, n, show_display=False):
    return client.call(proto.LiskGetAddress(address_n=n, show_display=show_display))


@expect(proto.LiskPublicKey)
def get_public_key(client, n, show_display=False):
    return client.call(proto.LiskGetPublicKey(address_n=n, show_display=show_display))


@expect(proto.LiskMessageSignature)
def sign_message(client, n, message):
    message = normalize_nfc(message)
    return client.call(proto.LiskSignMessage(address_n=n, message=message))


def verify_message(client, pubkey, signature, message):
    message = normalize_nfc(message)
    try:
        resp = client.call(
            proto.LiskVerifyMessage(
                signature=signature, public_key=pubkey, message=message
            )
        )
    except CallException as e:
        resp = e
    return isinstance(resp, proto.Success)


RENAMES = {"lifetime": "life_time", "keysgroup": "keys_group"}


@expect(proto.LiskSignedTx)
def sign_tx(client, n, transaction):
    transaction = dict_from_camelcase(transaction, renames=RENAMES)
    msg = dict_to_proto(proto.LiskTransactionCommon, transaction)
    return client.call(proto.LiskSignTx(address_n=n, transaction=msg))
