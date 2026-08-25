# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.crypto.hashlib import sha3_256

    from apps.ethereum.clear_signing_definitions import all_display_formats
    from apps.ethereum.yielding import (
        CLAIM_DISPLAY_FORMAT,
        DEPOSIT_DISPLAY_FORMAT,
        REDEEM_DISPLAY_FORMAT,
        WITHDRAW_DISPLAY_FORMAT,
    )

# Human-readable Solidity signatures for every function selector embedded in
# the firmware. The test recomputes keccak256(signature)[:4] for each entry
# and matches it against the binary `func_sig` actually stored in the shipped
# DisplayFormat objects, so a typo in a firmware selector (or a stale entry
# here) fails the test.
_SOLIDITY_SIGNATURES = (
    # ERC-20
    b"approve(address,uint256)",
    b"transfer(address,uint256)",
    # ERC-4626 vaults + Merkl claim (apps.ethereum.yielding)
    b"deposit(uint256,address)",
    b"withdraw(uint256,address,address)",
    b"redeem(uint256,address,address)",
    b"claim(address[],address[],uint256[],bytes32[][])",
    # WETH wrap/unwrap
    b"deposit()",
    b"withdraw(uint256)",
)


def _selector(signature: bytes) -> bytes:
    return sha3_256(signature, keccak=True).digest()[:4]


def _shipped_display_formats():
    yield from all_display_formats()
    yield DEPOSIT_DISPLAY_FORMAT
    yield WITHDRAW_DISPLAY_FORMAT
    yield REDEEM_DISPLAY_FORMAT
    yield CLAIM_DISPLAY_FORMAT


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumClearSigningDefinitions(unittest.TestCase):
    def test_func_sigs_match_solidity_signatures(self):
        expected = {_selector(sig): sig for sig in _SOLIDITY_SIGNATURES}
        # no duplicate entries / selector collisions in the table above
        self.assertEqual(len(expected), len(_SOLIDITY_SIGNATURES))

        seen = set()
        for display_format in _shipped_display_formats():
            func_sig = bytes(display_format.func_sig)
            if display_format.intent.startswith("Trezor Test"):
                # synthetic selectors of the debug-only test contracts must
                # not collide with any real function
                self.assertFalse(func_sig in expected)
                continue
            self.assertIn(
                func_sig,
                expected,
                msg=f"selector {func_sig.hex()} (intent {display_format.intent}) matches no known Solidity signature",
            )
            seen.add(func_sig)

        stale = sorted(expected[sel].decode() for sel in set(expected) - seen)
        self.assertFalse(
            stale, msg=f"signatures not used by any DisplayFormat: {stale}"
        )


if __name__ == "__main__":
    unittest.main()
