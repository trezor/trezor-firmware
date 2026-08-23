# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.crypto.hashlib import sha256
    from trezor.enums import StellarAssetType
    from trezor.messages import StellarAsset, StellarInvokeContractArgs

    from apps.stellar.consts import (
        NETWORK_PASSPHRASE_PUBLIC,
        NETWORK_PASSPHRASE_TESTNET,
    )
    from apps.stellar.helpers import STRKEY_CONTRACT, decode_strkey
    from apps.stellar.tokens import (
        NATIVE_TOKEN,
        PUBLIC_TOKENS,
        StellarToken,
        resolve_sep41_token,
        sac_address_from_asset,
    )


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


_SOLVBTC = "CBIJBDNZNF4X35BJ4FFZWCDBSCKOP5NB4PLG4SNENRMLAPYG4P5FM6VN"
# an ordinary contract, not a token known to the firmware
_UNKNOWN_CONTRACT = "CBIELTK6YBZJU5UP2WWQEUCYKLPU6AUNZ2BQ4WWFEIE3USCIHMXQDAMA"


def _transfer(contract, asset_hint=None):
    return StellarInvokeContractArgs(
        contract_address=contract,
        function_name="transfer",
        args=[],
        asset_hint=asset_hint,
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarResolveSep41Token(unittest.TestCase):
    def test_builtin_token_table(self):
        # A mistyped address would never match an invoked contract, leaving the
        # token silently unrecognized. decode_strkey verifies the CRC-16 and the
        # canonical encoding, so it catches exactly that.
        for contract in PUBLIC_TOKENS:
            version, _data = decode_strkey(contract)
            self.assertEqual(version, STRKEY_CONTRACT)

    def test_builtin_token(self):
        public_id = sha256(NETWORK_PASSPHRASE_PUBLIC.encode()).digest()
        testnet_id = sha256(NETWORK_PASSPHRASE_TESTNET.encode()).digest()

        token = resolve_sep41_token(_transfer(_SOLVBTC), public_id)
        self.assertEqual(token.symbol, "SolvBTC")
        self.assertEqual(token.decimals, 8)
        self.assertEqual(token.issuer, None)

        # the entry is bound to the public network
        self.assertEqual(resolve_sep41_token(_transfer(_SOLVBTC), testnet_id), None)
        # and anything else is left to the generic contract UI
        self.assertEqual(
            resolve_sep41_token(_transfer(_UNKNOWN_CONTRACT), public_id), None
        )

    def test_builtin_token_ignores_asset_hint(self):
        # a hint that does not derive to the invoked contract is discarded, so
        # a host cannot relabel a built-in token
        public_id = sha256(NETWORK_PASSPHRASE_PUBLIC.encode()).digest()
        hint = StellarAsset(
            type=StellarAssetType.ALPHANUM4,
            code="FAKE",
            issuer="GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN",
        )
        token = resolve_sep41_token(_transfer(_SOLVBTC, hint), public_id)
        self.assertEqual(token.symbol, "SolvBTC")
        self.assertEqual(token.decimals, 8)
        self.assertEqual(token.issuer, None)

    def test_sac_token(self):
        public_id = sha256(NETWORK_PASSPHRASE_PUBLIC.encode()).digest()
        issuer = "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN"
        usdc = StellarAsset(type=StellarAssetType.ALPHANUM4, code="USDC", issuer=issuer)
        usdc_sac = "CCW67TSZV3SSS2HXMBQ5JFGCKJNXKZM7UQUWUZPUTHXSTZLEO7SJMI75"

        token = resolve_sep41_token(_transfer(usdc_sac, usdc), public_id)
        self.assertEqual(token.symbol, "USDC")
        self.assertEqual(token.decimals, 7)
        self.assertEqual(token.issuer, issuer)

        # a hint that derives to some other contract is discarded
        eurc = StellarAsset(type=StellarAssetType.ALPHANUM4, code="EURC", issuer=issuer)
        self.assertEqual(
            resolve_sep41_token(_transfer(usdc_sac, eurc), public_id), None
        )

    def test_native_sac_ignores_code_and_issuer(self):
        # code and issuer are not part of a native asset and do not enter the
        # SAC address preimage, so a host must not be able to smuggle them in
        public_id = sha256(NETWORK_PASSPHRASE_PUBLIC.encode()).digest()
        native_sac = "CAS3J7GYLGXMF6TDJBBYYSE3HQ6BBSMLNUQ34T6TZMYMW2EVH34XOWMA"
        forged = StellarAsset(
            type=StellarAssetType.NATIVE,
            code="USDC",
            issuer="GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN",
        )
        token = resolve_sep41_token(_transfer(native_sac, forged), public_id)
        self.assertEqual(token.symbol, "XLM")
        self.assertEqual(token.decimals, 7)
        self.assertEqual(token.issuer, None)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarTokenFormat(unittest.TestCase):
    # Classic assets are always 7-decimal, but a SEP-41 token contract sets its
    # own precision and must not be rendered with the classic scale.
    def test_format(self):
        TESTS = [
            # the same amount, scaled by the token's own precision
            (200000000, 7, "XLM", "20 XLM"),
            (200000000, 8, "SolvBTC", "2 SolvBTC"),
        ]
        for amount, decimals, symbol, expected in TESTS:
            token = StellarToken(symbol, decimals, None)
            self.assertEqual(token.format(amount), expected)

    def test_format_native(self):
        self.assertEqual(NATIVE_TOKEN.format(200000000), "20 XLM")


if __name__ == "__main__":
    unittest.main()
