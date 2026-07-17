# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.crypto import base58

    from apps.ethereum.clear_signing_definitions import (
        APPROVE_DISPLAY_FORMAT,
        TRANSFER_DISPLAY_FORMAT,
    )

# (hex selector, Solidity function signature) pairs — each hardcoded selector
# must match the first 4 bytes of keccak256(signature).
_KNOWN_FUNC_SIGS = (
    ("095ea7b3", b"approve(address,uint256)"),
    ("a9059cbb", b"transfer(address,uint256)"),
    (
        "07ed2379",
        b"swap(address,(address,address,address,address,uint256,uint256,uint256),bytes)",
    ),
    ("83800a8e", b"unoswap(uint256,uint256,uint256,uint256)"),
    ("e2c95c82", b"unoswapTo(uint256,uint256,uint256,uint256,uint256)"),
    ("8770ba91", b"unoswap2(uint256,uint256,uint256,uint256,uint256)"),
    ("19367472", b"unoswap3(uint256,uint256,uint256,uint256,uint256,uint256)"),
    ("ea76dddf", b"unoswapTo2(uint256,uint256,uint256,uint256,uint256,uint256)"),
    (
        "f7a70056",
        b"unoswapTo3(uint256,uint256,uint256,uint256,uint256,uint256,uint256)",
    ),
    ("a76dfc3b", b"ethUnoswap(uint256,uint256)"),
    ("89af926a", b"ethUnoswap2(uint256,uint256,uint256)"),
    ("188ac35d", b"ethUnoswap3(uint256,uint256,uint256,uint256)"),
    ("175accdc", b"ethUnoswapTo(uint256,uint256,uint256)"),
    ("0f449d71", b"ethUnoswapTo2(uint256,uint256,uint256,uint256)"),
    ("493189f0", b"ethUnoswapTo3(uint256,uint256,uint256,uint256,uint256)"),
    (
        "5fd9ae2e",
        b"swapTokensMultipleV3ERC20ToERC20(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool)[])",
    ),
    (
        "2c57e884",
        b"swapTokensMultipleV3ERC20ToNative(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool)[])",
    ),
    (
        "736eac0b",
        b"swapTokensMultipleV3NativeToERC20(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool)[])",
    ),
    (
        "4666fc80",
        b"swapTokensSingleV3ERC20ToERC20(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool))",
    ),
    (
        "733214a3",
        b"swapTokensSingleV3ERC20ToNative(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool))",
    ),
    (
        "af7060fd",
        b"swapTokensSingleV3NativeToERC20(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool))",
    ),
    (
        "4630a0d8",
        b"swapTokensGeneric(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool)[])",
    ),
    ("b858183f", b"exactInput((bytes,address,uint256,uint256))"),
    (
        "04e45aaf",
        b"exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))",
    ),
    ("09b81346", b"exactOutput((bytes,address,uint256,uint256))"),
    (
        "5023b4df",
        b"exactOutputSingle((address,address,uint24,address,uint256,uint256,uint160))",
    ),
)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumClearSigningDefinitions(unittest.TestCase):
    def test_known_func_sigs(self):
        # Verify that every hardcoded function selector matches the first 4
        # bytes of keccak256 of its Solidity signature, so a typo cannot
        # silently match the wrong contract method.
        for hex_selector, signature in _KNOWN_FUNC_SIGS:
            self.assertEqual(
                bytes.fromhex(hex_selector),
                base58.keccak_32(signature),
                msg=f"selector mismatch for {signature.decode()}",
            )

    def test_approve_transfer_func_sigs(self):
        self.assertEqual(
            APPROVE_DISPLAY_FORMAT.func_sig,
            base58.keccak_32(b"approve(address,uint256)"),
        )
        self.assertEqual(
            TRANSFER_DISPLAY_FORMAT.func_sig,
            base58.keccak_32(b"transfer(address,uint256)"),
        )


if __name__ == "__main__":
    unittest.main()
