from common import unittest, await_result, H_

import storage.cache
from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256
from trezor.messages import AuthorizeCoinJoin
from trezor.messages import TxInput
from trezor.messages import TxOutput
from trezor.messages import SignTx
from trezor.messages import TxAckPaymentRequest
from trezor.enums import InputScriptType, OutputScriptType
from trezor.utils import HashWriter

from apps.common import coins
from apps.bitcoin.authorization import CoinJoinAuthorization
from apps.bitcoin.sign_tx.approvers import CoinJoinApprover
from apps.bitcoin.sign_tx.bitcoin import Bitcoin
from apps.bitcoin.sign_tx.tx_info import TxInfo
from apps.bitcoin import writers


class TestApprover(unittest.TestCase):

    def setUp(self):
        self.coin = coins.by_name('Bitcoin')
        self.max_fee_rate_percent = 0.3
        self.coordinator_name = "www.example.com"

        self.msg_auth = AuthorizeCoinJoin(
            coordinator=self.coordinator_name,
            max_rounds=10,
            max_coordinator_fee_rate=int(self.max_fee_rate_percent * 10**8),
            max_fee_per_kvbyte=7000,
            address_n=[H_(84), H_(0), H_(0)],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDWITNESS,
        )
        storage.cache.start_session()

    def test_coinjoin_lots_of_inputs(self):
        denomination = 10000000
        coordinator_fee = int(self.max_fee_rate_percent / 100 * denomination)
        fees = coordinator_fee + 500

        # Other's inputs.
        inputs = [
            TxInput(
                prev_hash=b"",
                prev_index=0,
                amount=denomination,
                script_pubkey=bytes(22),
                script_type=InputScriptType.EXTERNAL,
                sequence=0xffffffff,
                witness="",
            ) for i in range(99)
        ]

        # Our input.
        inputs.insert(30,
            TxInput(
                prev_hash=b"",
                prev_index=0,
                address_n=[H_(84), H_(0), H_(0), 0, 1],
                amount=denomination,
                script_type=InputScriptType.SPENDWITNESS,
                sequence=0xffffffff,
            )
        )

        # Other's CoinJoined outputs.
        outputs = [
            TxOutput(
                address="",
                amount=denomination-fees,
                script_type=OutputScriptType.PAYTOWITNESS,
                payment_req_index=0,
            ) for i in range(99)
        ]

        # Our CoinJoined output.
        outputs.insert(
            40,
            TxOutput(
                address="",
                address_n=[H_(84), H_(0), H_(0), 0, 2],
                amount=denomination-fees,
                script_type=OutputScriptType.PAYTOWITNESS,
                payment_req_index=0,
            )
        )

        # Coordinator's output.
        outputs.append(
            TxOutput(
                address="",
                amount=coordinator_fee * len(outputs),
                script_type=OutputScriptType.PAYTOWITNESS,
                payment_req_index=0,
            )
        )

        authorization = CoinJoinAuthorization(self.msg_auth)
        tx = SignTx(outputs_count=len(outputs), inputs_count=len(inputs), coin_name=self.coin.coin_name, lock_time=0)
        approver = CoinJoinApprover(tx, self.coin, authorization)
        signer = Bitcoin(tx, None, self.coin, approver)

        # Compute payment request signature.
        # Private key of m/0h for "all all ... all" seed.
        private_key = b'?S\ti\x8b\xc5o{,\xab\x03\x194\xea\xa8[_:\xeb\xdf\xce\xef\xe50\xf17D\x98`\xb9dj'
        h_pr = HashWriter(sha256())
        writers.write_bytes_fixed(h_pr, b"SL\x00\x24", 4)
        writers.write_bytes_prefixed(h_pr, b"")  # Empty nonce.
        writers.write_bytes_prefixed(h_pr, self.coordinator_name.encode())
        writers.write_compact_size(h_pr, 0)  # No memos.
        writers.write_uint32(h_pr, self.coin.slip44)
        h_outputs = HashWriter(sha256())
        for txo in outputs:
            writers.write_uint64(h_outputs, txo.amount)
            writers.write_bytes_prefixed(h_outputs, txo.address.encode())
        writers.write_bytes_fixed(h_pr, h_outputs.get_digest(), 32)
        signature = secp256k1.sign(private_key, h_pr.get_digest())

        tx_ack_payment_req = TxAckPaymentRequest(
            recipient_name=self.coordinator_name,
            signature=signature,
        )

        for txi in inputs:
            if txi.script_type == InputScriptType.EXTERNAL:
                approver.add_external_input(txi)
            else:
                await_result(approver.add_internal_input(txi))

        await_result(approver.add_payment_request(tx_ack_payment_req, None))
        for txo in outputs:
            if txo.address_n:
                approver.add_change_output(txo, script_pubkey=bytes(22))
            else:
                await_result(approver.add_external_output(txo, script_pubkey=bytes(22)))

        await_result(approver.approve_tx(TxInfo(signer, tx), []))

    def test_coinjoin_input_account_depth_mismatch(self):
        authorization = CoinJoinAuthorization(self.msg_auth)
        tx = SignTx(outputs_count=201, inputs_count=100, coin_name=self.coin.coin_name, lock_time=0)
        approver = CoinJoinApprover(tx, self.coin, authorization)

        txi = TxInput(
            prev_hash=b"",
            prev_index=0,
            address_n=[H_(49), H_(0), H_(0), 0],
            amount=10000000,
            script_type=InputScriptType.SPENDWITNESS
        )

        with self.assertRaises(wire.ProcessError):
            await_result(approver.add_internal_input(txi))

    def test_coinjoin_input_account_path_mismatch(self):
        authorization = CoinJoinAuthorization(self.msg_auth)
        tx = SignTx(outputs_count=201, inputs_count=100, coin_name=self.coin.coin_name, lock_time=0)
        approver = CoinJoinApprover(tx, self.coin, authorization)

        txi = TxInput(
            prev_hash=b"",
            prev_index=0,
            address_n=[H_(49), H_(0), H_(0), 0, 2],
            amount=10000000,
            script_type=InputScriptType.SPENDWITNESS
        )

        with self.assertRaises(wire.ProcessError):
            await_result(approver.add_internal_input(txi))


if __name__ == '__main__':
    unittest.main()
