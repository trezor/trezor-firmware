# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.wire import ProcessError

if not utils.BITCOIN_ONLY:
    from apps.stellar.helpers import (
        STRKEY_CLAIMABLE_BALANCE,
        STRKEY_CONTRACT,
        STRKEY_ED25519_PUBLIC_KEY,
        STRKEY_LIQUIDITY_POOL,
        STRKEY_MUXED_ACCOUNT,
        address_from_public_key,
        encode_strkey,
        public_key_from_address,
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarAddress(unittest.TestCase):
    def test_address_to_pubkey(self):
        self.assertEqual(
            public_key_from_address(
                "GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"
            ),
            unhexlify(
                "5d55642466b185b843152e9e219151dbc5892027ec40101a517bed5ca030c2e0"
            ),
        )

        self.assertEqual(
            public_key_from_address(
                "GCN2K2HG53AWX2SP5UHRPMJUUHLJF2XBTGSXROTPWRGAYJCDDP63J2U6"
            ),
            unhexlify(
                "9ba568e6eec16bea4fed0f17b134a1d692eae199a578ba6fb44c0c24431bfdb4"
            ),
        )

    def test_pubkey_to_address(self):
        addr = address_from_public_key(
            unhexlify(
                "5d55642466b185b843152e9e219151dbc5892027ec40101a517bed5ca030c2e0"
            )
        )
        self.assertEqual(
            addr, "GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"
        )

        addr = address_from_public_key(
            unhexlify(
                "9ba568e6eec16bea4fed0f17b134a1d692eae199a578ba6fb44c0c24431bfdb4"
            )
        )
        self.assertEqual(
            addr, "GCN2K2HG53AWX2SP5UHRPMJUUHLJF2XBTGSXROTPWRGAYJCDDP63J2U6"
        )

    def test_both(self):
        pubkey = unhexlify(
            "dfcc77d08588601702e02de2dc603f5c5281bea23baa894ae3b3b4778e5bbe40"
        )
        self.assertEqual(
            public_key_from_address(address_from_public_key(pubkey)), pubkey
        )

        pubkey = unhexlify(
            "53214e6155469c32fb882b1b1d94930d5445a78202867b7ddc6a33ad42ff4464"
        )
        self.assertEqual(
            public_key_from_address(address_from_public_key(pubkey)), pubkey
        )

        pubkey = unhexlify(
            "5ed4690134e5ef79b290ea1e7a4b8f3b6b3bcf287463c18bfe36baa030e7efbd"
        )
        self.assertEqual(
            public_key_from_address(address_from_public_key(pubkey)), pubkey
        )

    def test_invalid_address(self):
        with self.assertRaises(ProcessError):
            public_key_from_address(
                "GCN2K2HG53AWX2SP5UHRPMJUUHLJF2XBTGSXROTPWRGAYJCDDP63J2AA"
            )  # invalid checksum

    def test_encode_strkey_account(self):
        # Test encoding ED25519 public key (G... address)
        pubkey = unhexlify(
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"
        )
        self.assertEqual(
            encode_strkey(STRKEY_ED25519_PUBLIC_KEY, pubkey),
            "GA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVSGZ",
        )

    def test_encode_strkey_contract(self):
        # Test encoding contract address (C... address)
        contract_hash = unhexlify(
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"
        )
        self.assertEqual(
            encode_strkey(STRKEY_CONTRACT, contract_hash),
            "CA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUWDA",
        )

    # https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0023.md
    def test_encode_strkey_muxed_account(self):
        # Test encoding muxed account (M... address)
        # Muxed account is 32 bytes public key + 8 bytes ID
        # ed25519: GA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVSGZ
        # id: 9223372036854775808 (0x8000000000000000)
        muxed_data = unhexlify(
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"  # public key
            "8000000000000000"  # muxed ID
        )
        self.assertEqual(
            encode_strkey(STRKEY_MUXED_ACCOUNT, muxed_data),
            "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVAAAAAAAAAAAAAJLK",
        )

        # id: 0
        muxed_data = unhexlify(
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"  # public key
            "0000000000000000"  # muxed ID = 0
        )
        self.assertEqual(
            encode_strkey(STRKEY_MUXED_ACCOUNT, muxed_data),
            "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUAAAAAAAAAAAACJUQ",
        )

        # id: 1024
        muxed_data = unhexlify(
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"  # public key
            "0000000000000400"  # muxed ID = 1024
        )
        self.assertEqual(
            encode_strkey(STRKEY_MUXED_ACCOUNT, muxed_data),
            "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUAAAAAAAAAAEABLYI",
        )

    def test_encode_strkey_claimable_balance(self):
        # Test encoding claimable balance (B... address)
        # Claimable balance ID format: 1 bytes type (v0 = 0x00) + 32 bytes hash
        balance_id = unhexlify(
            "00"  # type v0
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"  # hash
        )
        self.assertEqual(
            encode_strkey(STRKEY_CLAIMABLE_BALANCE, balance_id),
            "BAAD6DBUX6J22DMZOHIEZTEQ64CVCHEDRKWZONFEUL5Q26QD7R76RGR4TU",
        )

    def test_encode_strkey_liquidity_pool(self):
        # Test encoding liquidity pool (L... address)
        # Liquidity pool ID is 32 bytes hash
        pool_id = unhexlify(
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"
        )
        self.assertEqual(
            encode_strkey(STRKEY_LIQUIDITY_POOL, pool_id),
            "LA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUPJN",
        )


if __name__ == "__main__":
    unittest.main()
