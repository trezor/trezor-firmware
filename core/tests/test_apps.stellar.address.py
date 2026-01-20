# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.wire import DataError

if not utils.BITCOIN_ONLY:
    from apps.stellar.helpers import (
        STRKEY_CLAIMABLE_BALANCE,
        STRKEY_CONTRACT,
        STRKEY_ED25519_PUBLIC_KEY,
        STRKEY_LIQUIDITY_POOL,
        STRKEY_MUXED_ACCOUNT,
        address_from_public_key,
        decode_strkey,
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
        with self.assertRaises(DataError):
            public_key_from_address(
                "GCN2K2HG53AWX2SP5UHRPMJUUHLJF2XBTGSXROTPWRGAYJCDDP63J2AA"
            )  # invalid checksum

    # Strkey round-trip test vectors from SEP-0023 "Valid test cases":
    # https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0023.md#tests
    # Each case asserts both directions: encode_strkey(version, data) -> strkey
    # and decode_strkey(strkey) -> (version, data).
    def test_strkey_account(self):
        # ED25519 public key (G... address)
        pubkey = unhexlify(
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"
        )
        strkey = "GA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVSGZ"
        self.assertEqual(encode_strkey(STRKEY_ED25519_PUBLIC_KEY, pubkey), strkey)
        self.assertEqual(decode_strkey(strkey), (STRKEY_ED25519_PUBLIC_KEY, pubkey))

    def test_strkey_contract(self):
        # contract address (C... address)
        contract_hash = unhexlify(
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"
        )
        strkey = "CA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUWDA"
        self.assertEqual(encode_strkey(STRKEY_CONTRACT, contract_hash), strkey)
        self.assertEqual(decode_strkey(strkey), (STRKEY_CONTRACT, contract_hash))

    def test_strkey_muxed_account(self):
        # muxed account (M... address): 32 bytes public key + 8 bytes ID
        # ed25519: GA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVSGZ
        pubkey = "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"
        for muxed_id, strkey in (
            # id: 9223372036854775808 (0x8000000000000000)
            (
                "8000000000000000",
                "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVAAAAAAAAAAAAAJLK",
            ),
            # id: 0
            (
                "0000000000000000",
                "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUAAAAAAAAAAAACJUQ",
            ),
            # id: 1024 (extra variant, not part of SEP-0023; muxed addresses can
            # be generated at https://lab.stellar.org/account/muxed-create)
            (
                "0000000000000400",
                "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUAAAAAAAAAAEABLYI",
            ),
        ):
            muxed_data = unhexlify(pubkey + muxed_id)
            self.assertEqual(encode_strkey(STRKEY_MUXED_ACCOUNT, muxed_data), strkey)
            self.assertEqual(decode_strkey(strkey), (STRKEY_MUXED_ACCOUNT, muxed_data))

    def test_strkey_claimable_balance(self):
        # claimable balance (B... address): 1 byte type (v0 = 0x00) + 32 bytes hash
        balance_id = unhexlify(
            "00"  # type v0
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"  # hash
        )
        strkey = "BAAD6DBUX6J22DMZOHIEZTEQ64CVCHEDRKWZONFEUL5Q26QD7R76RGR4TU"
        self.assertEqual(encode_strkey(STRKEY_CLAIMABLE_BALANCE, balance_id), strkey)
        self.assertEqual(decode_strkey(strkey), (STRKEY_CLAIMABLE_BALANCE, balance_id))

    def test_strkey_liquidity_pool(self):
        # liquidity pool (L... address): 32 bytes hash
        pool_id = unhexlify(
            "3f0c34bf93ad0d9971d04ccc90f705511c838aad9734a4a2fb0d7a03fc7fe89a"
        )
        strkey = "LA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUPJN"
        self.assertEqual(encode_strkey(STRKEY_LIQUIDITY_POOL, pool_id), strkey)
        self.assertEqual(decode_strkey(strkey), (STRKEY_LIQUIDITY_POOL, pool_id))

    # Invalid test cases from SEP-0023, minus the P... (signed payload) vectors,
    # which are rejected as an unsupported strkey version.
    def test_decode_strkey_invalid(self):
        for strkey in (
            "GAAAAAAAACGC6",  # payload length 5, G expects 32
            "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUAAAAAAAAAAAACJUR",  # unused trailing bit not zero
            "GA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVSGZA",  # length 1 mod 8
            "GA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUACUSI",  # payload length 33, G expects 32
            "G47QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVP2I",  # non-zero algorithm bits
            "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVAAAAAAAAAAAAAJLKA",  # length 6 mod 8
            "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVAAAAAAAAAAAAAAV75I",  # payload length 41, M expects 40
            "M47QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUAAAAAAAAAAAACJUQ",  # non-zero algorithm bits
            "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUAAAAAAAAAAAACJUK===",  # explicit padding not allowed
            "MA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJUAAAAAAAAAAAACJUO",  # invalid checksum
            "BAAD6DBUX6J22DMZOHIEZTEQ64CVCHEDRKWZONFEUL5Q26QD7R76RGR4TV",  # unused trailing 2-bits not zero
            "BAAT6DBUX6J22DMZOHIEZTEQ64CVCHEDRKWZONFEUL5Q26QD7R76RGXACA",  # claimable balance type byte not v0
        ):
            with self.assertRaises((DataError, ValueError)):
                decode_strkey(strkey)

    def test_decode_strkey_invalid_payload_size(self):
        # a canonical strkey (valid checksum) whose payload length does not
        # match its version is rejected
        TESTS = [
            (STRKEY_ED25519_PUBLIC_KEY, 31),  # G expects 32
            (STRKEY_ED25519_PUBLIC_KEY, 33),
            (STRKEY_CONTRACT, 33),  # C expects 32
            (STRKEY_MUXED_ACCOUNT, 32),  # M expects 40
            (STRKEY_CLAIMABLE_BALANCE, 32),  # B expects 33
            (STRKEY_LIQUIDITY_POOL, 31),  # L expects 32
        ]
        for version, size in TESTS:
            strkey = encode_strkey(version, bytes(size))
            with self.assertRaises(DataError):
                decode_strkey(strkey)


if __name__ == "__main__":
    unittest.main()
