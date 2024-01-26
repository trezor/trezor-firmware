from common import H_, unittest  # isort:skip

import storage.cache
from trezor.enums import InputScriptType
from trezor.messages import AuthorizeCoinJoin, GetOwnershipProof, SignTx

from apps.bitcoin.authorization import CoinJoinAuthorization
from apps.common import coins

_ROUND_ID_LEN = 32


class TestAuthorization(unittest.TestCase):

    coin = coins.by_name("Bitcoin")

    def setUp(self):
        self.msg_auth = AuthorizeCoinJoin(
            coordinator="www.example.com",
            max_rounds=3,
            max_coordinator_fee_rate=int(0.3 * 10**8),
            max_fee_per_kvbyte=7000,
            address_n=[H_(84), H_(0), H_(0)],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDWITNESS,
        )

        self.authorization = CoinJoinAuthorization(self.msg_auth)
        storage.cache.start_session()

    def test_ownership_proof_account_depth_mismatch(self):
        # Account depth mismatch.
        msg = GetOwnershipProof(
            address_n=[H_(84), H_(0), H_(0), 1],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.com"
            + int.to_bytes(1, _ROUND_ID_LEN, "big"),
        )

        self.assertFalse(self.authorization.check_get_ownership_proof(msg))

    def test_ownership_proof_account_path_mismatch(self):
        # Account path mismatch.
        msg = GetOwnershipProof(
            address_n=[H_(49), H_(0), H_(0), 1, 2],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.com"
            + int.to_bytes(1, _ROUND_ID_LEN, "big"),
        )

        self.assertFalse(self.authorization.check_get_ownership_proof(msg))

    def test_ownership_proof_coordinator_mismatch(self):
        # Coordinator name mismatch.
        msg = GetOwnershipProof(
            address_n=[H_(84), H_(0), H_(0), 1, 2],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.org"
            + int.to_bytes(1, _ROUND_ID_LEN, "big"),
        )

        self.assertFalse(self.authorization.check_get_ownership_proof(msg))

    def test_ownership_proof_wrong_coordinator_length(self):
        msg = GetOwnershipProof(
            address_n=[H_(84), H_(0), H_(0), 1, 2],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x0ewww.example.com"
            + int.to_bytes(1, _ROUND_ID_LEN - 1, "big"),
        )

        self.assertFalse(self.authorization.check_get_ownership_proof(msg))

        msg = GetOwnershipProof(
            address_n=[H_(84), H_(0), H_(0), 1, 2],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x10www.example.com"
            + int.to_bytes(1, _ROUND_ID_LEN + 1, "big"),
        )

        self.assertFalse(self.authorization.check_get_ownership_proof(msg))

    def test_authorize_ownership_proof(self):

        msg = GetOwnershipProof(
            address_n=[H_(84), H_(0), H_(0), 1, 2],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDWITNESS,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.com"
            + int.to_bytes(1, _ROUND_ID_LEN, "big"),
        )

        self.assertTrue(self.authorization.check_get_ownership_proof(msg))

    def test_approve_sign_tx(self):

        msg = SignTx(
            outputs_count=10,
            inputs_count=21,
            coin_name=self.coin.coin_name,
            lock_time=0,
        )

        self.assertTrue(self.authorization.approve_sign_tx(msg))
        self.assertTrue(self.authorization.approve_sign_tx(msg))
        self.assertTrue(self.authorization.approve_sign_tx(msg))
        self.assertFalse(self.authorization.approve_sign_tx(msg))


if __name__ == "__main__":
    unittest.main()
