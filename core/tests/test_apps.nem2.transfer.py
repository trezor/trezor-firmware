from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.mosaic import *
    from apps.nem2.transfer import *
    from apps.nem2.transfer.serialize import *
    from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction
    from trezor.messages.NEM2SignTx import NEM2SignTx


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2Transfer(unittest.TestCase):

    def test_create_transfer(self):

        # http://api-01.mt.us-west-2.nemtech.network:3000/transaction/8729BE2004B61CFFCEC2B7264DAF48A0F7E952258269C176BB678C385366E373
        m = _create_msg(NEM2_NETWORK_MIJIN_TEST,
                        NEM2_TRANSACTION_TYPE_TRANSFER,
                        36865,
                        20000,
                        113248176649,
                        "SAIKV5OOWCQ3EHIBMJH7HR2GGKPXUG2VT4OE3FU7",
                        0)

        t = serialize_transfer(m.transaction, m.transfer, unhexlify('90BA6CA2244CEA2E1826F3D93A22DA11284924814C4D63F43CD81FD28D228BE3'))

        self.assertEqual(t, unhexlify('A500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001905441204E00000000000071A2155C1A0000009010AAF5CEB0A1B21D01624FF3C746329F7A1B559F1C4D969F01000100C47BCD9047148F3000CA9A3B00000000'))
        # self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('0acbf8df91e6a65dc56c56c43d65f31ff2a6a48d06fc66e78c7f3436faf3e74f'))

def _create_msg(network_type: int, tx_type: int, version: int, max_fee: int,
                deadline: int, recipient_address: bytearray, num_mosaics: int):
    m = NEM2SignTx()
    m.transaction = NEM2TransactionCommon()
    m.transaction.network_type = network_type
    m.transaction.type = tx_type
    m.transaction.version = version
    m.transaction.max_fee = max_fee
    m.transaction.deadline = deadline
    m.transfer = NEM2TransferTransaction()
    m.transfer.recipient_address = recipient_address
    m.transfer.mosaics = list()
    for i in range(num_mosaics):
        m.transfer.mosaics.append(NEM2Mosaic())
    return m


if __name__ == '__main__':
    unittest.main()
