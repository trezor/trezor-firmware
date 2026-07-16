# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.crypto import base58

    from apps.ethereum import yielding


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumYielding(unittest.TestCase):
    def test_known_func_sigs(self):
        # Verify that the hardcoded ERC-4626 / claim function selectors match
        # the keccak256 of their signatures, so a typo cannot silently match
        # the wrong contract method.
        self.assertEqual(
            yielding.FUNC_SIG_DEPOSIT,
            base58.keccak_32(b"deposit(uint256,address)"),
        )
        self.assertEqual(
            yielding.FUNC_SIG_WITHDRAW,
            base58.keccak_32(b"withdraw(uint256,address,address)"),
        )
        self.assertEqual(
            yielding.FUNC_SIG_REDEEM,
            base58.keccak_32(b"redeem(uint256,address,address)"),
        )
        self.assertEqual(
            yielding.FUNC_SIG_CLAIM,
            base58.keccak_32(b"claim(address[],address[],uint256[],bytes32[][])"),
        )

    def test_known_address(self):
        # https://etherscan.io/address/0x3ef3d8ba38ebe18db133cec108f4d14ce00dd9ae
        self.assertEqual(
            yielding._MERKL_XYZ_CLAIM_DISTRIBUTOR_ADDR,
            unhexlify("3ef3d8ba38ebe18db133cec108f4d14ce00dd9ae"),
        )


if __name__ == "__main__":
    unittest.main()
