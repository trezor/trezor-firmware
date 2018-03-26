from common import *

from apps.nem.transaction import *
from apps.nem.multisig import *


class TestNemMultisig(unittest.TestCase):

    def test_nem_multisig(self):
        # http://bob.nem.ninja:8765/#/multisig/7d3a7087023ee29005262016706818579a2b5499eb9ca76bad98c1e6f4c46642

        base_tx = nem_transaction_create_aggregate_modification(NEM_NETWORK_TESTNET,
                                                                3939039,
                                                                unhexlify("abac2ee3d4aaa7a3bfb65261a00cc04c761521527dd3f2cf741e2815cbba83ac"),
                                                                16000000,
                                                                3960639,
                                                                1,
                                                                False)

        base_tx = nem_transaction_write_cosignatory_modification(base_tx, 2, unhexlify("e6cff9b3725a91f31089c3acca0fac3e341c00b1c8c6e9578f66c4514509c3b3"))
        multisig = nem_transaction_create_multisig(NEM_NETWORK_TESTNET,
                                                   3939039,
                                                   unhexlify("59d89076964742ef2a2089d26a5aa1d2c7a7bb052a46c1de159891e91ad3d76e"),
                                                   6000000,
                                                   3960639,
                                                   base_tx)

        self.assertEqual(multisig, unhexlify("0410000001000098df1a3c002000000059d89076964742ef2a2089d26a5aa1d2c7a7bb052a46c1de159891e91ad3d76e808d5b00000000003f6f3c006c0000000110000001000098df1a3c0020000000abac2ee3d4aaa7a3bfb65261a00cc04c761521527dd3f2cf741e2815cbba83ac0024f400000000003f6f3c0001000000280000000200000020000000e6cff9b3725a91f31089c3acca0fac3e341c00b1c8c6e9578f66c4514509c3b3"))

        address = "TCRXYUQIMFA7AOGL5LF3YWLC7VABLYUMJ5ACBUNL"
        multisig = nem_transaction_create_multisig_signature(NEM_NETWORK_TESTNET,
                                                             3939891,
                                                             unhexlify("71cba4f2a28fd19f902ba40e9937994154d9eeaad0631d25d525ec37922567d4"),
                                                             6000000,
                                                             3961491,
                                                             base_tx,
                                                             address)

        self.assertEqual(multisig, unhexlify("0210000001000098331e3c002000000071cba4f2a28fd19f902ba40e9937994154d9eeaad0631d25d525ec37922567d4808d5b000000000093723c0024000000200000008ec165580bdabfd31ce6007a1748ce5bdf30eab7a214743097de3bc822ac7e002800000054435258595551494d464137414f474c354c463359574c43375641424c59554d4a35414342554e4c"))

    def test_nem_multisig_2(self):
        # http://chain.nem.ninja/#/multisig/1016cf3bdd61bd57b9b2b07b6ff2dee390279d8d899265bdc23d42360abe2e6c

        base_tx = nem_transaction_create_provision_namespace(NEM_NETWORK_MAINNET,
                                                             59414272,
                                                             unhexlify("a1df5306355766bd2f9a64efdc089eb294be265987b3359093ae474c051d7d5a"),
                                                             20000000,
                                                             59500672,
                                                             "dim",
                                                             "",
                                                             "NAMESPACEWH4MKFMBCVFERDPOOP4FK7MTBXDPZZA",
                                                             5000000000)

        multisig = nem_transaction_create_multisig(NEM_NETWORK_MAINNET,
                                                   59414272,
                                                   unhexlify("cfe58463f0eaebceb5d00717f8aead49171a5d7c08f6b1299bd534f11715acc9"),
                                                   6000000,
                                                   59500672,
                                                   base_tx)

        self.assertEqual(multisig, unhexlify("041000000100006800978a0320000000cfe58463f0eaebceb5d00717f8aead49171a5d7c08f6b1299bd534f11715acc9808d5b000000000080e88b037b000000012000000100006800978a0320000000a1df5306355766bd2f9a64efdc089eb294be265987b3359093ae474c051d7d5a002d31010000000080e88b03280000004e414d4553504143455748344d4b464d42435646455244504f4f5034464b374d54425844505a5a4100f2052a010000000300000064696dffffffff"))

        address = "NDDRG3UEB5LZZZMDWBE4RTKZK73JBHPAIWBHCFMV"
        multisig = nem_transaction_create_multisig_signature(NEM_NETWORK_MAINNET,
                                                             59414342,
                                                             unhexlify("1b49b80203007117d034e45234ffcdf402c044aeef6dbb06351f346ca892bce2"),
                                                             6000000,
                                                             59500742,
                                                             base_tx,
                                                             address)

        self.assertEqual(multisig, unhexlify("021000000100006846978a03200000001b49b80203007117d034e45234ffcdf402c044aeef6dbb06351f346ca892bce2808d5b0000000000c6e88b032400000020000000bfa2088f7720f89dd4664d650e321dabd02fab61b7355bc88a391a848a49786a280000004e4444524733554542354c5a5a5a4d445742453452544b5a4b37334a424850414957424843464d56"))

        multisig = nem_transaction_create_multisig_signature(NEM_NETWORK_MAINNET,
                                                             59414381,
                                                             unhexlify("7ba4b39209f1b9846b098fe43f74381e43cb2882ccde780f558a63355840aa87"),
                                                             6000000,
                                                             59500781,
                                                             base_tx,
                                                             address)

        self.assertEqual(multisig, unhexlify("02100000010000686d978a03200000007ba4b39209f1b9846b098fe43f74381e43cb2882ccde780f558a63355840aa87808d5b0000000000ede88b032400000020000000bfa2088f7720f89dd4664d650e321dabd02fab61b7355bc88a391a848a49786a280000004e4444524733554542354c5a5a5a4d445742453452544b5a4b37334a424850414957424843464d56"))


if __name__ == '__main__':
    unittest.main()
