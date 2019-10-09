from common import *

if not utils.BITCOIN_ONLY:
    from trezor.messages.RipplePayment import RipplePayment
    from trezor.messages.RippleSignerListSet import RippleSignerListSet
    from trezor.messages.RippleSignerEntry import RippleSignerEntry
    from trezor.messages.RippleAccountSet import RippleAccountSet
    from trezor.messages.RippleSignTx import RippleSignTx
    from apps.ripple.serialize import serialize, serialize_amount, serialize_raw
    from apps.ripple.sign_tx import get_network_prefix
    import apps.ripple.transaction_fields as tx_field
    from apps.ripple.binary_field import field as binfield


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestRippleSerializer(unittest.TestCase):
    def test_amount(self):
        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/fixtures/data-driven-tests.json#L2494
        self.assertEqual(serialize_amount(0), unhexlify("4000000000000000"))
        self.assertEqual(serialize_amount(1), unhexlify("4000000000000001"))
        self.assertEqual(serialize_amount(93493429243),
                         unhexlify("40000015c4a483fb"))
        with self.assertRaises(ValueError):
            serialize_amount(1000000000000000000)  # too large
        with self.assertRaises(ValueError):
            serialize_amount(-1)  # negative not supported
        with self.assertRaises(Exception):
            serialize_amount(1.1)  # float numbers not supported

    def test_transactions(self):
        # from https://github.com/miracle2k/ripple-python
        source_address = "r3P9vH81KBayazSTrQj6S25jW6kDb779Gi"
        payment = RipplePayment(
            amount=200000000, destination="r3kmLJN5D28dHuH8vZNUZpMC43pEHpaocV")
        common = RippleSignTx(fee=10, sequence=1, payment=payment)
        self.assertEqual(
            serialize(msg=common,
                      source_address=source_address,
                      multisig=False,
                      fields=tx_field.payment(common)),
            unhexlify(
                "120000240000000161400000000bebc20068400000000000000a811450f97a072f1c4357f1ad84566a609479d927c9428314550fc62003e785dc231a1058a05e56e3f09cf4e6"
            ))

        source_address = "r3kmLJN5D28dHuH8vZNUZpMC43pEHpaocV"
        payment = RipplePayment(
            amount=1, destination="r3P9vH81KBayazSTrQj6S25jW6kDb779Gi")
        common = RippleSignTx(fee=99, sequence=99, payment=payment)
        self.assertEqual(
            serialize(msg=common,
                      source_address=source_address,
                      multisig=False,
                      fields=tx_field.payment(common)),
            unhexlify(
                "12000024000000636140000000000000016840000000000000638114550fc62003e785dc231a1058a05e56e3f09cf4e6831450f97a072f1c4357f1ad84566a609479d927c942"
            ))

        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/fixtures/data-driven-tests.json#L1579
        source_address = "r9TeThyi5xiuUUrFjtPKZiHcDxs7K9H6Rb"
        payment = RipplePayment(25000000, "r4BPgS7DHebQiU31xWELvZawwSG2fSPJ7C")
        common = RippleSignTx(fee=10, flags=0, sequence=2, payment=payment)
        self.assertEqual(
            serialize(msg=common,
                      source_address=source_address,
                      multisig=False,
                      fields=tx_field.payment(common)),
            unhexlify(
                "120000220000000024000000026140000000017d784068400000000000000a81145ccb151f6e9d603f394ae778acf10d3bece874f68314e851bbbe79e328e43d68f43445368133df5fba5a"
            ))

        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/fixtures/data-driven-tests.json#L1651
        source_address = "rGWTUVmm1fB5QUjMYn8KfnyrFNgDiD9H9e"
        payment = RipplePayment(200000, "rw71Qs1UYQrSQ9hSgRohqNNQcyjCCfffkQ")
        common = RippleSignTx(fee=15, flags=0, sequence=144, payment=payment)
        # 201b005ee9ba removed from the test vector because last ledger sequence is not supported
        self.assertEqual(
            serialize(msg=common,
                      source_address=source_address,
                      multisig=False,
                      fields=tx_field.payment(common)),
            unhexlify(
                "12000022000000002400000090614000000000030d4068400000000000000f8114aa1bd19d9e87be8069fdbf6843653c43837c03c6831467fe6ec28e0464dd24fb2d62a492aac697cfad02"
            ))

        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/fixtures/data-driven-tests.json#L1732
        source_address = "r4BPgS7DHebQiU31xWELvZawwSG2fSPJ7C"
        payment = RipplePayment(25000000, "rBqSFEFg2B6GBMobtxnU1eLA1zbNC9NDGM",
                                4146942154)
        common = RippleSignTx(fee=12, flags=0, sequence=1, payment=payment)
        self.assertEqual(
            serialize(msg=common,
                      source_address=source_address,
                      multisig=False,
                      fields=tx_field.payment(common)),
            unhexlify(
                "120000220000000024000000012ef72d50ca6140000000017d784068400000000000000c8114e851bbbe79e328e43d68f43445368133df5fba5a831476dac5e814cd4aa74142c3ab45e69a900e637aa2"
            ))

        # original
        source_address = "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H"
        signer_entries = [
            RippleSignerEntry("rh5ZnEVySAy7oGd3nebT3wrohGDrsNS83E", 1),
            RippleSignerEntry("rNaj2u1NQWwy6WLy294wZs1jhuz1Q8PNof", 1)
        ]
        signer_list_set = RippleSignerListSet(signer_quorum=1,
                                              signer_entries=signer_entries)
        common = RippleSignTx(fee=12,
                              flags=2147483648,
                              sequence=1,
                              signer_list_set=signer_list_set)
        self.assertEqual(
            serialize(msg=common,
                      source_address=source_address,
                      multisig=False,
                      fields=tx_field.signer_list_set(common)),
            unhexlify(
                "12000c2280000000240000000120230000000168400000000000000c81148fb40e1ffa5d557ce9851a535af94965e0dd0988f4eb130001811428c4348871a02d480ffdf2f192110185db13cfd9e1eb13000181148faf434d5f7d95d4904ea2f07dce37f370574ab7e1f1"
            ))

        # DisableMaster flag
        source_address = "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H"
        account_set = RippleAccountSet(set_flag=4)
        common = RippleSignTx(fee=12,
                              flags=2147483648,
                              sequence=6,
                              account_set=account_set)
        self.assertEqual(
            serialize(msg=common,
                      source_address=source_address,
                      multisig=False,
                      fields=tx_field.account_set(common)),
            unhexlify(
                "1200032280000000240000000620210000000468400000000000000c81148fb40e1ffa5d557ce9851a535af94965e0dd0988"
            ))

        tx_dict = {
            "TransactionType": binfield["TRANSACTION_TYPES"]["Payment"],
            "Flags": 0,
            "Sequence": 32,
            "LastLedgerSequence": 500000,
            "Fee": 12,
            "Account": "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H",
            "Amount": 22000000,
            "Destination": "rJX2KwzaLJDyFhhtXKi3htaLfaUH2tptEX",
            "DestinationTag": 810
        }
        self.assertEqual(
            serialize_raw(fields=tx_dict, isSigning=False),
            unhexlify(
                "120000220000000024000000202E0000032A201B0007A1206140000000014FB18068400000000000000C81148FB40E1FFA5D557CE9851A535AF94965E0DD09888314C0426CFCB532E7523BD87B14E12C24C85121AAAA"
            ))

    def test_transactions_for_signing(self):
        # https://github.com/ripple/ripple-binary-codec/blob/4581f1b41e712f545ba08be15e188a557c731ecf/test/signing-data-encoding-test.js
        source_address = "r9LqNeG6qHxjeUocjvVki2XR35weJ9mZgQ"
        payment = RipplePayment(1000, "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh")
        common = RippleSignTx(fee=10,
                              flags=2147483648,
                              sequence=1,
                              payment=payment)
        tx = serialize(
            msg=common,
            source_address=source_address,
            multisig=False,
            fields=tx_field.payment(common),
            pubkey=unhexlify(
                "ed5f5ac8b98974a3ca843326d9b88cebd0560177b973ee0b149f782cfaa06dc66a"
            ),
        )
        tx = get_network_prefix(multisig=False) + tx

        self.assertEqual(tx[0:4], unhexlify("53545800"))  # signing prefix
        self.assertEqual(tx[4:7], unhexlify("120000"))  # transaction type
        self.assertEqual(tx[7:12], unhexlify("2280000000"))  # flags
        self.assertEqual(tx[12:17], unhexlify("2400000001"))  # sequence
        self.assertEqual(tx[17:26], unhexlify("6140000000000003e8"))  # amount
        self.assertEqual(tx[26:35], unhexlify("68400000000000000a"))  # fee
        self.assertEqual(
            tx[35:70],
            unhexlify(
                "7321ed5f5ac8b98974a3ca843326d9b88cebd0560177b973ee0b149f782cfaa06dc66a"
            ))  # signing pub key
        self.assertEqual(
            tx[70:92], unhexlify(
                "81145b812c9d57731e27a2da8b1830195f88ef32a3b6"))  # account
        self.assertEqual(
            tx[92:114],
            unhexlify(
                "8314b5f762798a53d543a014caf8b297cff8f2f937e8"))  # destination
        self.assertEqual(len(tx[114:]), 0)  # that's it


if __name__ == "__main__":
    unittest.main()
