import binascii
from trezorlib import nem


def test_nem_basic():
    transaction = {
        "timeStamp": 76809215,
        "amount": 1000000,
        "fee": 1000000,
        "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
        "type": nem.TYPE_TRANSACTION_TRANSFER,
        "deadline": 76895615,
        "version": (0x98 << 24),
        "message": {
            "payload": binascii.hexlify(b'hello world'),
            "type": 1,
        },
        "mosaics": [
            {
                "mosaicId": {
                    "namespaceId": "nem",
                    "name": "xem",
                },
                "quantity": 1000000,
            },
        ],
    }

    msg = nem.create_sign_tx(transaction)

    # this is basically just a random sampling of expected properties
    assert msg.transaction is not None
    assert msg.transfer is not None
    assert len(msg.transfer.mosaics) == 1
    assert msg.transfer.mosaics[0].namespace == "nem"

    assert msg.aggregate_modification is None
    assert msg.provision_namespace is None
