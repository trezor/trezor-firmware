from common import unittest, await_result, H_

from trezor import wire
from trezor.messages.AuthorizeCoinJoin import AuthorizeCoinJoin
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.SignTx import SignTx
from trezor.messages import InputScriptType, OutputScriptType

from apps.common import coins
from apps.bitcoin.authorization import CoinJoinAuthorization
from apps.bitcoin.sign_tx.approvers import CoinJoinApprover


class TestApprover(unittest.TestCase):

    def setUp(self):
        self.coin = coins.by_name('Bitcoin')
        self.fee_per_anonymity_percent = 0.003

        self.msg_auth = AuthorizeCoinJoin(
            coordinator="www.example.com",
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
            TxInputType(
                amount=denomination + 1000000 * (i + 1),
                script_type=InputScriptType.EXTERNAL,
                sequence=0xffffffff,
            ) for i in range(99)
        ]

        # Our input.
        inputs.insert(
            30,
            TxInputType(
                address_n=[H_(84), H_(0), H_(0), 0, 1],
                amount=denomination + 1000000,
                script_type=InputScriptType.SPENDWITNESS,
                sequence=0xffffffff,
            )
        )

        # Other's CoinJoined outputs.
        outputs = [
            TxOutputType(
                amount=denomination,
                script_type=OutputScriptType.PAYTOWITNESS,
            ) for i in range(99)
        ]

        # Our CoinJoined output.
        outputs.insert(
            40,
            TxOutputType(
                address_n=[H_(84), H_(0), H_(0), 0, 2],
                amount=denomination,
                script_type=OutputScriptType.PAYTOWITNESS,
            )
        )

        coordinator_fee = self.fee_per_anonymity_percent / 100 * len(outputs) * denomination
        fees = coordinator_fee + 10000
        total_coordinator_fee = coordinator_fee * len(outputs)

        # Other's change-outputs.
        outputs.extend(
            TxOutputType(
                amount=1000000 * (i + 1) - fees,
                script_type=OutputScriptType.PAYTOWITNESS,
            ) for i in range(99)
        )

        # Our change-output.
        outputs.append(
            TxOutputType(
                address_n=[H_(84), H_(0), H_(0), 1, 1],
                amount=1000000 - fees,
                script_type=OutputScriptType.PAYTOWITNESS,
            )
        )

        # Coordinator's output.
        outputs.append(
            TxOutputType(
                amount=total_coordinator_fee,
                script_type=OutputScriptType.PAYTOWITNESS,
            )
        )

        authorization = CoinJoinAuthorization(self.msg_auth, None, self.coin)
        tx = SignTx(outputs_count=len(outputs), inputs_count=len(inputs), coin_name=self.coin.coin_name, lock_time=0)
        approver = CoinJoinApprover(tx, self.coin, authorization)

        for txi in inputs:
            if txi.script_type == InputScriptType.EXTERNAL:
                approver.add_external_input(txi)
            else:
                await_result(approver.add_internal_input(txi))

        for txo in outputs:
            if txo.address_n:
                approver.add_change_output(txo, script_pubkey=bytes(22))
            else:
                await_result(approver.add_external_output(txo, script_pubkey=bytes(22)))

        await_result(approver.approve_tx())

    def test_coinjoin_input_account_depth_mismatch(self):
        authorization = CoinJoinAuthorization(self.msg_auth, None, self.coin)
        tx = SignTx(outputs_count=201, inputs_count=100, coin_name=self.coin.coin_name, lock_time=0)
        approver = CoinJoinApprover(tx, self.coin, authorization)

        txi = TxInputType(
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

        txi = TxInputType(
            address_n=[H_(49), H_(0), H_(0), 0, 2],
            amount=10000000,
            script_type=InputScriptType.SPENDWITNESS
        )

        with self.assertRaises(wire.ProcessError):
            await_result(approver.add_internal_input(txi))


if __name__ == '__main__':
    unittest.main()
