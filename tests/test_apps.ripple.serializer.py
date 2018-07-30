from common import *
from apps.ripple.serialize import serialize
from apps.ripple.serialize import serialize_amount
from apps.ripple.sign_tx import get_network_prefix
from trezor.messages.RippleSignTx import RippleSignTx
from trezor.messages.RipplePayment import RipplePayment


class TestRippleSerializer(unittest.TestCase):

    def test_amount(self):
        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/fixtures/data-driven-tests.json#L2494
        assert serialize_amount(0) == unhexlify('4000000000000000')
        assert serialize_amount(1) == unhexlify('4000000000000001')
        assert serialize_amount(93493429243) == unhexlify('40000015c4a483fb')
        with self.assertRaises(ValueError):
            serialize_amount(1000000000000000000)  # too large
        with self.assertRaises(ValueError):
            serialize_amount(-1)  # negative not supported
        with self.assertRaises(ValueError):
            serialize_amount(1.1)  # float numbers not supported

    def test_transactions(self):
        # from https://github.com/miracle2k/ripple-python
        source_address = 'r3P9vH81KBayazSTrQj6S25jW6kDb779Gi'
        payment = RipplePayment(200000000, 'r3kmLJN5D28dHuH8vZNUZpMC43pEHpaocV')
        common = RippleSignTx(None, 10, None, 1, None, payment)
        assert serialize(common, source_address) == unhexlify('120000240000000161400000000bebc20068400000000000000a811450f97a072f1c4357f1ad84566a609479d927c9428314550fc62003e785dc231a1058a05e56e3f09cf4e6')

        source_address = 'r3kmLJN5D28dHuH8vZNUZpMC43pEHpaocV'
        payment = RipplePayment(1, 'r3P9vH81KBayazSTrQj6S25jW6kDb779Gi')
        common = RippleSignTx(None, 99, None, 99, None, payment)
        assert serialize(common, source_address) == unhexlify('12000024000000636140000000000000016840000000000000638114550fc62003e785dc231a1058a05e56e3f09cf4e6831450f97a072f1c4357f1ad84566a609479d927c942')

        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/fixtures/data-driven-tests.json#L1579
        source_address = 'r9TeThyi5xiuUUrFjtPKZiHcDxs7K9H6Rb'
        payment = RipplePayment(25000000, 'r4BPgS7DHebQiU31xWELvZawwSG2fSPJ7C')
        common = RippleSignTx(None, 10, 0, 2, None, payment)
        assert serialize(common, source_address) == unhexlify('120000220000000024000000026140000000017d784068400000000000000a81145ccb151f6e9d603f394ae778acf10d3bece874f68314e851bbbe79e328e43d68f43445368133df5fba5a')

        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/fixtures/data-driven-tests.json#L1651
        source_address = 'rGWTUVmm1fB5QUjMYn8KfnyrFNgDiD9H9e'
        payment = RipplePayment(200000, 'rw71Qs1UYQrSQ9hSgRohqNNQcyjCCfffkQ')
        common = RippleSignTx(None, 15, 0, 144, None, payment)
        # 201b005ee9ba removed from the test vector because last ledger sequence is not supported
        assert serialize(common, source_address) == unhexlify('12000022000000002400000090614000000000030d4068400000000000000f8114aa1bd19d9e87be8069fdbf6843653c43837c03c6831467fe6ec28e0464dd24fb2d62a492aac697cfad02')

        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/fixtures/data-driven-tests.json#L1732
        source_address = 'r4BPgS7DHebQiU31xWELvZawwSG2fSPJ7C'
        payment = RipplePayment(25000000, 'rBqSFEFg2B6GBMobtxnU1eLA1zbNC9NDGM')
        common = RippleSignTx(None, 12, 0, 1, None, payment)
        # 2ef72d50ca removed from the test vector because destination tag is not supported
        assert serialize(common, source_address) == unhexlify('120000220000000024000000016140000000017d784068400000000000000c8114e851bbbe79e328e43d68f43445368133df5fba5a831476dac5e814cd4aa74142c3ab45e69a900e637aa2')

    def test_transactions_for_signing(self):
        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/signing-data-encoding-test.js
        source_address = 'r9LqNeG6qHxjeUocjvVki2XR35weJ9mZgQ'
        payment = RipplePayment(1000, 'rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh')
        common = RippleSignTx(None, 10, 2147483648, 1, None, payment)

        tx = serialize(common, source_address, pubkey=unhexlify('ed5f5ac8b98974a3ca843326d9b88cebd0560177b973ee0b149f782cfaa06dc66a'))
        tx = get_network_prefix() + tx

        assert tx[0:4] == unhexlify('53545800')  # signing prefix
        assert tx[4:7] == unhexlify('120000')  # transaction type
        assert tx[7:12] == unhexlify('2280000000')  # flags
        assert tx[12:17] == unhexlify('2400000001')  # sequence
        assert tx[17:26] == unhexlify('6140000000000003e8')  # amount
        assert tx[26:35] == unhexlify('68400000000000000a')  # fee
        assert tx[35:70] == unhexlify('7321ed5f5ac8b98974a3ca843326d9b88cebd0560177b973ee0b149f782cfaa06dc66a')  # singing pub key
        assert tx[70:92] == unhexlify('81145b812c9d57731e27a2da8b1830195f88ef32a3b6')  # account
        assert tx[92:114] == unhexlify('8314b5f762798a53d543a014caf8b297cff8f2f937e8')  # destination
        assert len(tx[114:]) == 0  # that's it


if __name__ == '__main__':
    unittest.main()
