from common import *

from trezor.crypto import beam

from apps.beam.helpers import (
    bin_to_str,
)
from apps.beam.nonce import *
from trezor.pin import pin_to_int


def __init_and_unlock_config():
    config.init()
    config.wipe()
    config.unlock(pin_to_int(''))


class TestBeamGenerateNonce(unittest.TestCase):
    mnemonic = "all all all all all all all all all all all all"
    seed = beam.from_mnemonic_beam(mnemonic)

    def test_master_nonce(self):
        self.assertEqual(is_master_nonce_created(), False)

        config.init()
        config.wipe()
        config.unlock(pin_to_int(''))
        self.assertEqual(is_master_nonce_created(), False)

        create_master_nonce(self.seed)
        self.assertEqual(is_master_nonce_created(), True)

    def test_generate_nonce_singular(self):
        test_datasets = (
            (
                1,
                "907356940fcc255479509517cfb381ea8c97631f116da551e1dbe958cb74977f", 0
            ),
            (
                2,
                "7245e95ad17cea33fd91dffa041c93e6258c679a62651e0f155b253c29c0f4e4", 1
            ),
            (
                3,
                "222f20219e08ab207b483d2bcb989b646281cf95b83ec35bf01246c9c24861ad", 0
            ),
            (
                4,
                "18d2ac3f9dbc3d686352ce45390951077c1cb882cb8cf84ed2aaa32d0eaf6f0d", 1
            ),
            (
                5,
                "18b34cb39a4a9e54dd71ffb7898ae29263fa7ea80048caa03dd39e3516b35237", 1
            ),
            (
                6,
                "0643ac518336207ac327652d4266728afb30f99c772263caff38aee4f797c8a6", 0
            ),
            (
                7,
                "ea0f4dc9323d9ebb323db74a7505220ce964a9a4f2f7b3f984b3ae17dcac8847", 1
            ),
            (
                8,
                "f0ff98f3a9a6e49f0560789e56ffec9b9d30d026a4f7a3f3e88ad8b4cdd8c6ce", 1
            ),
            (
                9,
                "59bf7dfce1afcb1147a9057640fbc74c054702b798da6dccaa09c08f8e023eab", 0
            ),
            (
                10,
                "c63be273d84be79bf5ee205b13cdca7aad711ee87bf0d96cf602b252ac4e51de", 1
            ),
        )

        __init_and_unlock_config()
        create_master_nonce(self.seed)

        for test_params in test_datasets:
            slot = test_params[0]
            expected_pub_x = test_params[1]
            expected_pub_y = test_params[2]

            _, new_nonce = create_nonce(slot)
            pubkey_x, pubkey_y = calc_nonce_pub(new_nonce)

            self.assertEqual(bin_to_str(pubkey_x), expected_pub_x)
            self.assertEqual(pubkey_y[0], expected_pub_y)

    def test_get_nonce_public(self):
        test_datasets = (
            (
                1,
                "bc47be20f12041a1cbd1c9265b8397ed8249972ca3510629a5c6e3bd3e6e2793", 0,
            ),
            (
                2,
                "86820dfa982357dc9bebf7e0aa24bd800e29e9372b2c745545c037988ea1666f", 0,
            ),
            (
                3,
                "eff59e168bbfbb8696e0b695ab135a8e51d677dd11f4d444a4209c028ae43c44", 0
            ),
            (
                4,
                "dc6192e3822950ee14c277aa16891461936d23aac6a283f26d1cf5580b9b286f", 1
            ),
            (
                5,
                "309567c913ca0474491f9ed08e1d1da35a4c2f3a4db6c9d610220c6ccc1114d5", 0
            ),
            (
                6,
                "2b070adfe1c6090280f48ea3d36e6fcd5ffe50bb5e9084af710b67786dce78af", 1
            ),
            (
                7,
                "b941e433e0be60152fc7f0fefd9a2e539186dd7691c2acd040e86b89ded1732d", 1
            ),
            (
                8,
                "a106ba444dc58efd0e7deacfae276a71970eb446aaa641aff31a0818400c52fa", 0
            ),
            (
                9,
                "71d12f75072c62f2e2d41dcb9c06d5f1341412a189deb5e01ec007b3770fdd48", 1
            ),
            (
                10,
                "4b66d33ab72fb6e30f7d3d265bb2132129dfa783ef0063514adc68f2da6a5699", 0
            ),
            (
                11,
                "5f5afc9f87d9c5420007bb43f5b18b08c1ffda5095c3b85045e82248b74a4973", 0
            ),
            (
                14,
                "77e8da5f5f89c5aeea33b74c20f03e9ad56ae34c693ca52722ee04eb53a04af4", 0
            ),
            (
                15,
                "620033e2630dbd511bfd93e39af7a3ab7d18545d985fd21317b8689dd007f9cb", 0
            ),
            (
                20,
                "4cfcfd48404e59952f3a777eef412726475fab8de47bc09515e74f923cba5d9b", 0
            ),
            (
                42,
                "91079d4dd75e709e705db7bbfcdb4ac8f7c20aad91b259fba608bd3d1d1578f6", 0
            ),
        )

        __init_and_unlock_config()
        create_master_nonce(self.seed)

        for test_params in test_datasets:
            slot = test_params[0]
            expected_pub_x = test_params[1]
            expected_pub_y = test_params[2]

            pubkey_x, pubkey_y = get_nonce_pub(slot)

            self.assertEqual(bin_to_str(pubkey_x), expected_pub_x)
            self.assertEqual(pubkey_y[0], expected_pub_y)

    def test_consume_nonce(self):
        test_datasets = (
            (
                # Slot number
                1,
                (
                    # Expected public keys (each next result is influenced by previous)
                    ("bc47be20f12041a1cbd1c9265b8397ed8249972ca3510629a5c6e3bd3e6e2793", 0),
                    ("907356940fcc255479509517cfb381ea8c97631f116da551e1dbe958cb74977f", 0),
                ),
            ),
            (
                # Slot number
                2,
                (
                    # Expected public keys (each next result is influenced by previous)
                    ("86820dfa982357dc9bebf7e0aa24bd800e29e9372b2c745545c037988ea1666f", 0),
                    ("7245e95ad17cea33fd91dffa041c93e6258c679a62651e0f155b253c29c0f4e4", 1),
                    ("e548866f0aabe149f3111ad69b3eb49fd5955356ac01404e89ac8f5d652a20da", 1),
                    ("df449a81066451123154ce2894f1d2cac88cf079a76a9016c94937b3934a9ad5", 1),
                    ("5ac9af998e236b01c5b8623fd8a59a30bf4884cd1c633ba717362428739a8107", 1),
                ),
            ),
            (
                # Slot number
                20,
                (
                    # Expected public keys (each next result is influenced by previous)
                    ("4cfcfd48404e59952f3a777eef412726475fab8de47bc09515e74f923cba5d9b", 0),
                    ("93062b41367dcf42b77b5b712d4dd3cec5b34e80defc750a4748e7e03b643027", 1),
                    ("9c2e6c6ce8627be88e1165ed7fbc2f7d88483c59e904ff7d27e734c412747b72", 1),
                    ("749532358b78ed8be86c4022e8241fe8a9198ce4c6f974300bfc072b67517fa7", 1),
                    ("baa63f8cbabcfa115ade13fd876c959cc38467e9e80e052916e51f21de79ec58", 0),
                    ("e3bf982bb5a4c49e449e7f82fb0b74fa60bb1ba033b7891797e1694969fd5630", 1),
                ),
            ),
            (
                # Slot number
                42,
                (
                    # Expected public keys (each next result is influenced by previous)
                    ("91079d4dd75e709e705db7bbfcdb4ac8f7c20aad91b259fba608bd3d1d1578f6", 0),
                    ("43b867b1d20d303652879902f67c4e6bfc602429e414d9035a160c60e4d97a34", 0),
                    ("1fca3baba4542ac31bde0ca854c2df5ee0490be6c37d9fa9ee7b81a4fea01198", 1),
                    ("76c2ee37fce19ee912c765f9a1e1a6c477a7eae61903f60bdea263ba602faa99", 1),
                    ("12e4d7efeee2950637b700bb1a11884af585ac15b38166b2af181af36f2126ae", 0),
                    ("f8db921a659decdbf67556bdd11d4c416d796a8c21303f06913b89755a639f14", 0),
                    ("cd62c77950f269d0fa9d24d08418c1c1cda6f820acfa65a23ec15373cfeeceb5", 0),
                    ("a90626fe6ca8ff9c295a0476c6635c27b8db52fb0e1ebac5df7b948733f0eb99", 1),
                ),
            ),
        )

        __init_and_unlock_config()
        create_master_nonce(self.seed)

        for test_params in test_datasets:
            slot = test_params[0]

            expected_derivables = test_params[1]
            for expected in expected_derivables:
                expected_pub_x = expected[0]
                expected_pub_y = expected[1]

                pubkey_x, pubkey_y = get_nonce_pub(slot)
                consume_nonce(slot)

                #print("Slot: {}; X: {}; Y: {}".format(slot, bin_to_str(pubkey_x), pubkey_y[0]))
                self.assertEqual(bin_to_str(pubkey_x), expected_pub_x)
                self.assertEqual(pubkey_y[0], expected_pub_y)

    def test_generate_nonce_derived(self):
        test_datasets = (
            (
                # Slot number
                1,
                (
                    # Expected derivables (each next result is influenced by previous)
                    ("907356940fcc255479509517cfb381ea8c97631f116da551e1dbe958cb74977f", 0),
                    ("dd54c9e2da23f6918547f884dfe998db4a8724654c772c7e113f897c3c9aa414", 1),
                ),
            ),
            (
                # Slot number
                2,
                (
                    # Expected derivables (each next result is influenced by previous)
                    ("7245e95ad17cea33fd91dffa041c93e6258c679a62651e0f155b253c29c0f4e4", 1),
                    ("e548866f0aabe149f3111ad69b3eb49fd5955356ac01404e89ac8f5d652a20da", 1),
                    ("df449a81066451123154ce2894f1d2cac88cf079a76a9016c94937b3934a9ad5", 1),
                    ("5ac9af998e236b01c5b8623fd8a59a30bf4884cd1c633ba717362428739a8107", 1),
                ),
            ),
            (
                # Slot number
                20,
                (
                    # Expected derivables (each next result is influenced by previous)
                    ("93062b41367dcf42b77b5b712d4dd3cec5b34e80defc750a4748e7e03b643027", 1),
                    ("9c2e6c6ce8627be88e1165ed7fbc2f7d88483c59e904ff7d27e734c412747b72", 1),
                    ("749532358b78ed8be86c4022e8241fe8a9198ce4c6f974300bfc072b67517fa7", 1),
                    ("baa63f8cbabcfa115ade13fd876c959cc38467e9e80e052916e51f21de79ec58", 0),
                    ("e3bf982bb5a4c49e449e7f82fb0b74fa60bb1ba033b7891797e1694969fd5630", 1),
                ),
            ),
            (
                # Slot number
                42,
                (
                    # Expected derivables (each next result is influenced by previous)
                    ("43b867b1d20d303652879902f67c4e6bfc602429e414d9035a160c60e4d97a34", 0),
                    ("1fca3baba4542ac31bde0ca854c2df5ee0490be6c37d9fa9ee7b81a4fea01198", 1),
                    ("76c2ee37fce19ee912c765f9a1e1a6c477a7eae61903f60bdea263ba602faa99", 1),
                    ("12e4d7efeee2950637b700bb1a11884af585ac15b38166b2af181af36f2126ae", 0),
                    ("f8db921a659decdbf67556bdd11d4c416d796a8c21303f06913b89755a639f14", 0),
                    ("cd62c77950f269d0fa9d24d08418c1c1cda6f820acfa65a23ec15373cfeeceb5", 0),
                    ("a90626fe6ca8ff9c295a0476c6635c27b8db52fb0e1ebac5df7b948733f0eb99", 1),
                ),
            ),
        )

        __init_and_unlock_config()
        create_master_nonce(self.seed)

        for test_params in test_datasets:
            slot = test_params[0]

            expected_derivables = test_params[1]
            for expected in expected_derivables:
                expected_pub_x = expected[0]
                expected_pub_y = expected[1]

                _, new_nonce = create_nonce(slot)
                pubkey_x, pubkey_y = calc_nonce_pub(new_nonce)

                self.assertEqual(bin_to_str(pubkey_x), expected_pub_x)
                self.assertEqual(pubkey_y[0], expected_pub_y)


if __name__ == '__main__':
    unittest.main()

