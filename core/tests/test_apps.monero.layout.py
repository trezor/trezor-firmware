# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.enums import MoneroNetworkType
    from trezor.messages import (
        MoneroAccountPublicAddress,
        MoneroTransactionData,
        MoneroTransactionDestinationEntry,
    )

    from apps.monero import layout


PAYMENT_ID = b"\xde\xad\xbe\xef\xde\xad\xbe\xef"


class _Progress:
    """Stands in for MoneroTransactionProgress, which needs a real State."""

    def step(self, state, step, sub_step=0):
        pass


def _addr(tag: int) -> "MoneroAccountPublicAddress":
    return MoneroAccountPublicAddress(
        spend_public_key=bytes([tag]) * 32,
        view_public_key=bytes([tag + 1]) * 32,
    )


def _dst(tag: int, amount: int) -> "MoneroTransactionDestinationEntry":
    return MoneroTransactionDestinationEntry(
        amount=amount, addr=_addr(tag), is_subaddress=False
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroLayout(unittest.TestCase):
    """
    require_confirm_transaction must display any payment id that will end up in the
    signed transaction. The decision may not depend on integrated_indices being
    well-formed -- it is host-controlled and validated nowhere.
    """

    def setUp(self):
        self.shown_outputs = []
        self.shown_payment_ids = []
        self.originals = {
            name: getattr(layout, name)
            for name in (
                "_require_confirm_output",
                "_require_confirm_payment_id",
                "_require_confirm_fee",
            )
        }

        async def confirm_output(dst, network_type, payment_id, chunkify):
            self.shown_outputs.append((dst, payment_id))

        async def confirm_payment_id(payment_id):
            self.shown_payment_ids.append(payment_id)

        async def confirm_fee(fee):
            pass

        layout._require_confirm_output = confirm_output
        layout._require_confirm_payment_id = confirm_payment_id
        layout._require_confirm_fee = confirm_fee

    def tearDown(self):
        for name, original in self.originals.items():
            setattr(layout, name, original)

    def _confirm(self, outputs, change_dts, payment_id, integrated_indices):
        tsx_data = MoneroTransactionData(
            outputs=outputs,
            change_dts=change_dts,
            fee=1000,
            payment_id=payment_id,
            integrated_indices=integrated_indices,
        )
        await_result(
            layout.require_confirm_transaction(
                None, tsx_data, MoneroNetworkType.MAINNET, _Progress()
            )
        )

    def _with_change(self, payment_id, integrated_indices):
        """One real output at index 0, change at index 1."""
        change = _dst(20, 500)
        self._confirm([_dst(10, 100), change], change, payment_id, integrated_indices)

    def _with_dummy(self, payment_id, integrated_indices):
        """One real output at index 0, zero-amount dummy at index 1, no change."""
        self._confirm(
            [_dst(10, 100), _dst(20, 0)], None, payment_id, integrated_indices
        )

    # --- the reported bypass -------------------------------------------------

    def test_change_index_still_confirms(self):
        # integrated_indices names the change output, which is never displayed
        self._with_change(PAYMENT_ID, [1])
        self.assertEqual(self.shown_payment_ids, [PAYMENT_ID])
        self.assertEqual(len(self.shown_outputs), 1)
        self.assertIsNone(self.shown_outputs[0][1])

    def test_dummy_index_still_confirms(self):
        # integrated_indices names the dummy output, which is never displayed
        self._with_dummy(PAYMENT_ID, [1])
        self.assertEqual(self.shown_payment_ids, [PAYMENT_ID])
        self.assertEqual(len(self.shown_outputs), 1)
        self.assertIsNone(self.shown_outputs[0][1])

    def test_out_of_range_index_still_confirms(self):
        # an index that matches no output at all -- needs no change output to work
        self._with_change(PAYMENT_ID, [999])
        self.assertEqual(self.shown_payment_ids, [PAYMENT_ID])

    def test_partially_matching_indices_confirm_once(self):
        # index 0 is displayed, index 999 is not; the id is shown with the output
        self._with_change(PAYMENT_ID, [0, 999])
        self.assertEqual(self.shown_payment_ids, [])
        self.assertEqual(self.shown_outputs[0][1], PAYMENT_ID)

    # --- honest flows must be unaffected -------------------------------------

    def test_integrated_address_shows_id_with_output(self):
        self._with_change(PAYMENT_ID, [0])
        self.assertEqual(self.shown_payment_ids, [])
        self.assertEqual(len(self.shown_outputs), 1)
        self.assertEqual(self.shown_outputs[0][1], PAYMENT_ID)

    def test_explicit_payment_id_without_indices(self):
        self._with_change(PAYMENT_ID, [])
        self.assertEqual(self.shown_payment_ids, [PAYMENT_ID])
        self.assertIsNone(self.shown_outputs[0][1])

    def test_no_payment_id(self):
        self._with_change(None, [])
        self.assertEqual(self.shown_payment_ids, [])
        self.assertIsNone(self.shown_outputs[0][1])

    def test_dummy_payment_id_is_not_confirmed(self):
        # the uniformity dummy id carries no information and stays hidden
        self._with_change(layout.DUMMY_PAYMENT_ID, [])
        self.assertEqual(self.shown_payment_ids, [])


if __name__ == "__main__":
    unittest.main()
