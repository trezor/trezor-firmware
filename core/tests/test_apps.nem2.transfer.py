from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem.helpers import *
    from apps.nem.mosaic import *
    from apps.nem.transfer import *
    from apps.nem.transfer.serialize import *
    from trezor.messages.NEMTransfer import NEMTransfer
    from trezor.messages.NEMSignTx import NEMSignTx


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2Transfer(unittest.TestCase):

    def test_create_transfer(self):

        # http://api-01.mt.us-west-2.nemtech.network:3000/transaction/8729BE2004B61CFFCEC2B7264DAF48A0F7E952258269C176BB678C385366E373
        m = _create_msg(NEM2_NETWORK_MIJIN_TEST,
                        0,
                        0,
                        0,
                        'TBGIMRE4SBFRUJXMH7DVF2IBY36L2EDWZ37GVSC4',
                        50000000000000)

        t = serialize_transfer(m.transaction, m.transfer, unhexlify('e59ef184a612d4c3c4d89b5950eb57262c69862b2f96e59c5043bf41765c482f'))


        self.assertEqual(t, unhexlify('01010000010000980000000020000000e59ef184a612d4c3c4d89b5950eb57262c69862b2f96e59c5043bf41765c482f00000000000000000000000028000000544247494d52453453424652554a584d48374456463249425933364c324544575a3337475653433400203d88792d000000000000'))
        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('0acbf8df91e6a65dc56c56c43d65f31ff2a6a48d06fc66e78c7f3436faf3e74f'))






def _create_msg(network: int, timestamp: int, fee: int, deadline: int,
                recipient: str, amount: int):
    m = NEM2SignTx()
    m.transaction = NEM2TransactionCommon()
    m.transaction.type = tx_type
    m.transaction.network_type = network_type
    m.transaction.version = version
    m.transaction.max_fee = max_fee
    m.transaction.deadline = deadline
    m.transfer = NEM2TransferTransaction()
    m.transfer.recipient_address = recipient_address
    m.transfer.mosaics = list()
    for i in range(mosaics):
        m.transfer.mosaics.append(NEM2Mosaic(
            id=""
        ))
    return m


if __name__ == '__main__':
    unittest.main()
