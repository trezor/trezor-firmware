# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.enums import MoneroNetworkType
    from trezor.messages import (
        MoneroAccountPublicAddress,
        MoneroTransactionDestinationEntry,
    )

    from apps.monero.signing import ChangeAddressError
    from apps.monero.signing.state import State
    from apps.monero.signing.step_01_init_transaction import (
        _check_change,
        _get_primary_change_address,
    )
    from apps.monero.xmr import crypto, crypto_helpers
    from apps.monero.xmr.credentials import AccountCreds


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroCheckChange(unittest.TestCase):
    """
    `_check_change` is the only thing standing between a malicious host and an
    output keyed as change (a*R) in step 6. Cover every branch, including the
    sweep exemption, where the change address is deliberately *not* ours.
    """

    def setUp(self):
        self.state = State()
        self.state.creds = AccountCreds.new_wallet(
            crypto_helpers.decodeint(
                bytes.fromhex(
                    "4ce88c168e0f5f8d6524f712d5f8d7d83233b1e7a2a60b5aba5206cc0ea2bc08"
                )
            ),
            crypto_helpers.decodeint(
                bytes.fromhex(
                    "f2644a3dd97d43e87887e74d1691d52baa0614206ad1b0c239ff4aa3b501750a"
                )
            ),
            network_type=MoneroNetworkType.TESTNET,
        )
        self.state.account_idx = 0
        # our own primary change address for account 0
        self.ours = _get_primary_change_address(self.state)
        # two unrelated addresses: a payment recipient and wallet2's throwaway
        # address for the 0-amount fake output of a sweep
        self.recipient = self._foreign_addr()
        self.dummy = self._foreign_addr()

    def _foreign_addr(self):
        spend = crypto.scalarmult_base_into(None, crypto.random_scalar())
        view = crypto.scalarmult_base_into(None, crypto.random_scalar())
        return MoneroAccountPublicAddress(
            spend_public_key=crypto_helpers.encodepoint(spend),
            view_public_key=crypto_helpers.encodepoint(view),
        )

    def _dst(self, amount, addr, is_subaddress=False):
        return MoneroTransactionDestinationEntry(
            amount=amount, addr=addr, is_subaddress=is_subaddress
        )

    def _check(self, change_dts, outputs):
        self.state.output_change = change_dts
        _check_change(self.state, outputs)

    # --- sweep shape ---------------------------------------------------------

    def test_sweep_is_accepted(self):
        # What wallet2 actually emits: the change entry *is* the 0-amount fake
        # output, sent to a random address that is not ours.
        change = self._dst(0, self.dummy)
        outputs = [self._dst(1000, self.recipient), self._dst(0, self.dummy)]
        self._check(change, outputs)

    def test_sweep_change_aliasing_recipient_is_rejected(self):
        # Malicious host points the unvalidated change address at the paying
        # output, so step 6 would key it with our own view key (a*R).
        change = self._dst(0, self.recipient)
        outputs = [self._dst(1000, self.recipient), self._dst(0, self.dummy)]
        with self.assertRaises(ChangeAddressError):
            self._check(change, outputs)

    def test_sweep_change_aliasing_subaddress_recipient_is_rejected(self):
        # Same poison against a subaddress recipient. Besides the a*R branch,
        # this would also hide the recipient from classify_subaddresses and
        # suppress the ADDITIONAL_PUBKEYS the recipient needs to scan.
        change = self._dst(0, self.recipient)
        outputs = [
            self._dst(1000, self.recipient, is_subaddress=True),
            self._dst(0, self.dummy),
        ]
        with self.assertRaises(ChangeAddressError):
            self._check(change, outputs)

    def test_sweep_change_aliasing_the_fake_output_is_accepted(self):
        # The fake output carries no money, so keying it as change is harmless.
        change = self._dst(0, self.dummy)
        outputs = [self._dst(1000, self.recipient), self._dst(0, self.dummy)]
        self._check(change, outputs)

    def test_sweep_shape_with_our_own_change_is_accepted(self):
        change = self._dst(0, self.ours)
        outputs = [self._dst(1000, self.recipient), self._dst(0, self.ours)]
        self._check(change, outputs)

    def test_sweep_to_our_primary_address_is_accepted(self):
        # If the fake sweep output aliases our own primary address, step 6 still derives
        # the same one-time key for the paying output (`a*R == r*A`).
        change = self._dst(0, self.ours)
        outputs = [self._dst(1000, self.ours), self._dst(0, self.ours)]
        self._check(change, outputs)

    # --- non-sweep shapes ----------------------------------------------------

    def test_no_change(self):
        self._check(None, [self._dst(1000, self.recipient), self._dst(0, self.dummy)])

    def test_change_to_ourselves(self):
        change = self._dst(500, self.ours)
        outputs = [self._dst(1000, self.recipient), self._dst(500, self.ours)]
        self._check(change, outputs)

    def test_foreign_change_is_rejected(self):
        change = self._dst(500, self.recipient)
        outputs = [self._dst(1000, self.recipient), self._dst(500, self.recipient)]
        with self.assertRaises(ChangeAddressError):
            self._check(change, outputs)

    def test_change_not_among_outputs_is_rejected(self):
        change = self._dst(500, self.ours)
        outputs = [self._dst(1000, self.recipient), self._dst(500, self.dummy)]
        with self.assertRaises(ChangeAddressError):
            self._check(change, outputs)

    def test_three_outputs_with_foreign_change_is_rejected(self):
        # The sweep exemption must not extend past two outputs.
        change = self._dst(0, self.recipient)
        outputs = [
            self._dst(1000, self.recipient),
            self._dst(0, self.dummy),
            self._dst(0, self.dummy),
        ]
        with self.assertRaises(ChangeAddressError):
            self._check(change, outputs)


if __name__ == "__main__":
    unittest.main()
