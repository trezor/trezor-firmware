# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.crypto.hashlib import sha256
    from trezor.enums import StellarAssetType
    from trezor.messages import StellarAsset

    from apps.stellar.consts import (
        NETWORK_PASSPHRASE_PUBLIC,
        NETWORK_PASSPHRASE_TESTNET,
    )
    from apps.stellar.tokens import sac_address_from_asset


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarTokens(unittest.TestCase):
    # Expected addresses cross-checked against stellar_sdk's
    # Asset.contract_id(); the PUBLIC USDC one is Circle's well-known SAC.
    def test_sac_address_from_asset(self):
        native = StellarAsset(type=StellarAssetType.NATIVE)
        usdc = StellarAsset(  # ALPHANUM4
            type=StellarAssetType.ALPHANUM4,
            code="USDC",
            issuer="GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN",
        )
        ustry = StellarAsset(  # ALPHANUM12
            type=StellarAssetType.ALPHANUM12,
            code="USTRY",
            issuer="GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC",
        )
        # the same asset resolves to a different contract on each network
        VECTORS = (
            (
                NETWORK_PASSPHRASE_PUBLIC,
                native,
                "CAS3J7GYLGXMF6TDJBBYYSE3HQ6BBSMLNUQ34T6TZMYMW2EVH34XOWMA",
            ),
            (
                NETWORK_PASSPHRASE_PUBLIC,
                usdc,
                "CCW67TSZV3SSS2HXMBQ5JFGCKJNXKZM7UQUWUZPUTHXSTZLEO7SJMI75",
            ),
            (
                NETWORK_PASSPHRASE_PUBLIC,
                ustry,
                "CBLV4ATSIWU67CFSQU2NVRKINQIKUZ2ODSZBUJTJ43VJVRSBTZYOPNUR",
            ),
            (
                NETWORK_PASSPHRASE_TESTNET,
                native,
                "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
            ),
            (
                NETWORK_PASSPHRASE_TESTNET,
                usdc,
                "CA2E53VHFZ6YSWQIEIPBXJQGT6VW3VKWWZO555XKRQXYJ63GEBJJGHY7",
            ),
            (
                NETWORK_PASSPHRASE_TESTNET,
                ustry,
                "CBEHZAPSMUJXT6R4X4LSQYEOOSNBNUQISUTHJNDZKMPSZQEKJC753HR3",
            ),
        )
        for passphrase, asset, expected in VECTORS:
            network_id = sha256(passphrase.encode()).digest()
            self.assertEqual(sac_address_from_asset(network_id, asset), expected)


if __name__ == "__main__":
    unittest.main()
