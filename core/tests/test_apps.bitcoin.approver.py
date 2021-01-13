from common import unittest, await_result, H_

from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256
from trezor.messages.AuthorizeCoinJoin import AuthorizeCoinJoin
from trezor.messages.TxAckPaymentRequest import TxAckPaymentRequest
from trezor.messages.TxInput import TxInput
from trezor.messages.TxOutput import TxOutput
from trezor.messages.SignTx import SignTx
from trezor.messages import InputScriptType, OutputScriptType
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
        self.fee_per_anonymity_percent = 0.003
        self.coordinator_name = "www.example.com"

        self.msg_auth = AuthorizeCoinJoin(
            coordinator=self.coordinator_name,
            max_total_fee=40000,
            fee_per_anonymity=self.fee_per_anonymity_percent * 10**9,
            address_n=[H_(84), H_(0), H_(0)],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDWITNESS,
        )

    def test_coinjoin_lots_of_inputs(self):
        denomination = 10000000

        # Other's inputs.
        inputs = [
            TxInput(
                prev_hash=b"",
                prev_index=0,
                amount=denomination + 1000000 * (i + 1),
                script_type=InputScriptType.EXTERNAL,
                sequence=0xffffffff,
            ) for i in range(99)
        ]

        # Our input.
        inputs.insert(
            30,
            TxInput(
                prev_hash=b"",
                prev_index=0,
                address_n=[H_(84), H_(0), H_(0), 0, 1],
                amount=denomination + 1000000,
                script_type=InputScriptType.SPENDWITNESS,
                sequence=0xffffffff,
            )
        )

        # Other's CoinJoined outputs.
        outputs = [
            TxOutput(
                amount=denomination,
                script_type=OutputScriptType.PAYTOWITNESS,
                payment_req_index=0,
            ) for i in range(99)
        ]

        # Our CoinJoined output.
        outputs.insert(
            40,
            TxOutput(
                address_n=[H_(84), H_(0), H_(0), 0, 2],
                amount=denomination,
                script_type=OutputScriptType.PAYTOWITNESS,
                payment_req_index=0,
            )
        )

        coordinator_fee = int(self.fee_per_anonymity_percent / 100 * len(outputs) * denomination)
        fees = coordinator_fee + 10000
        total_coordinator_fee = coordinator_fee * len(outputs)

        # Other's change-outputs.
        outputs.extend(
            TxOutput(
                amount=1000000 * (i + 1) - fees,
                script_type=OutputScriptType.PAYTOWITNESS,
                payment_req_index=0,
            ) for i in range(99)
        )

        # Our change-output.
        outputs.append(
            TxOutput(
                address_n=[H_(84), H_(0), H_(0), 1, 1],
                amount=1000000 - fees,
                script_type=OutputScriptType.PAYTOWITNESS,
                payment_req_index=0,
            )
        )

        # Coordinator's output.
        outputs.append(
            TxOutput(
                amount=total_coordinator_fee,
                script_type=OutputScriptType.PAYTOWITNESS,
                payment_req_index=0,
            )
        )

        authorization = CoinJoinAuthorization(self.msg_auth, None, self.coin)
        tx = SignTx(outputs_count=len(outputs), inputs_count=len(inputs), coin_name=self.coin.coin_name, lock_time=0)
        approver = CoinJoinApprover(tx, self.coin, authorization)
        signer = Bitcoin(tx, None, self.coin, approver)

        hash_outputs = b's\xe3\xda\x1b;\x8c\x99*\xf5X\xbf(\xe52R\xa2A\x87 \xae\xf1:H=\xa8\x9c\x80\xf1\xe6\xb6%('

        # Compute payment request signature.
        # Private key of m/0h for "all all ... all" seed.
        private_key = b'?S\ti\x8b\xc5o{,\xab\x03\x194\xea\xa8[_:\xeb\xdf\xce\xef\xe50\xf17D\x98`\xb9dj'
        h_pr = HashWriter(sha256())
        writers.write_bytes_fixed(h_pr, b"Payment request:", 16)
        writers.write_bytes_prefixed(h_pr, b"")  # Empty nonce.
        writers.write_bytes_prefixed(h_pr, self.coordinator_name.encode())
        writers.write_bitcoin_varint(h_pr, 0)  # No memos.
        writers.write_uint32(h_pr, self.coin.slip44)
        writers.write_bytes_fixed(h_pr, hash_outputs, 32)
        signature = secp256k1.sign(private_key, h_pr.get_digest())

        tx_ack_payment_req = TxAckPaymentRequest(
            recipient_name=self.coordinator_name,
            amount=5929040000,
            signature=signature,
        )

        for txi in inputs:
            if txi.script_type == InputScriptType.EXTERNAL:
                approver.add_external_input(txi)
            else:
                await_result(approver.add_internal_input(txi))

        for i, txo in enumerate(outputs):
            if txo.address_n:
                approver.add_change_output(txo, script_pubkey=bytes(22))
            else:
                await_result(approver.add_external_output(txo, script_pubkey=bytes(22)))

            if i == 0:
                await_result(approver.add_payment_request(tx_ack_payment_req, None))

        await_result(approver.approve_tx(TxInfo(signer, tx), []))

    def test_coinjoin_input_account_depth_mismatch(self):
        authorization = CoinJoinAuthorization(self.msg_auth, None, self.coin)
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
        authorization = CoinJoinAuthorization(self.msg_auth, None, self.coin)
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
