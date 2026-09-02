# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.messages import (
        MoneroAccountPublicAddress,
        MoneroTransactionData,
        MoneroTransactionDestinationEntry,
    )

    from apps.monero.signing import step_01_init_transaction


def _dst(tag: int, amount: int) -> "MoneroTransactionDestinationEntry":
    return MoneroTransactionDestinationEntry(
        amount=amount,
        addr=MoneroAccountPublicAddress(
            spend_public_key=bytes([tag]) * 32,
            view_public_key=bytes([tag + 1]) * 32,
        ),
        is_subaddress=False,
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroCheckPaymentId(unittest.TestCase):
    """
    A payment id that cannot go into a transaction must be rejected before the
    confirmation dialog renders it into an integrated address -- encode_addr
    appends whatever length it is given.
    """

    def _check(self, payment_id, integrated_indices):
        change = _dst(20, 500)
        tsx_data = MoneroTransactionData(
            outputs=[_dst(10, 100), change],
            change_dts=change,
            fee=1000,
            payment_id=payment_id,
            integrated_indices=integrated_indices,
        )
        step_01_init_transaction._check_payment_id(tsx_data)

    def test_wrong_length_is_rejected(self):
        with self.assertRaises(ValueError):
            self._check(b"\x01\x02\x03\x04\x05", [])

    def test_long_payment_id_cannot_be_integrated(self):
        # there is no 32-byte integrated address
        with self.assertRaises(ValueError):
            self._check(bytes(range(32)), [0])

    def test_short_payment_id_can_be_integrated(self):
        self._check(bytes(range(8)), [0])

    def test_short_payment_id_without_indices(self):
        self._check(bytes(range(8)), [])

    def test_long_payment_id_without_indices(self):
        # 32 bytes is the plaintext form
        self._check(bytes(range(32)), [])

    def test_no_payment_id(self):
        self._check(None, [])

    def test_empty_payment_id(self):
        # the client may send the field as empty bytes rather than omitting it;
        # _process_payment_id writes nothing for it, so it must not be rejected
        self._check(b"", [])

    def test_empty_payment_id_with_indices(self):
        self._check(b"", [0])


if __name__ == "__main__":
    unittest.main()
