# flake8: noqa: F403,F405
from common import *  # isort:skip

import storage.cache_codec
from trezor import wire
from trezor.crypto import bip32
from trezor.enums import InputScriptType, OutputScriptType
from trezor.messages import (
    AuthorizeCoinJoin,
    CoinJoinRequest,
    SignTx,
    TxInput,
    TxOutput,
)

from apps.bitcoin.authorization import FEE_RATE_DECIMALS, CoinJoinAuthorization
from apps.bitcoin.sign_tx.approvers import BasicApprover, CoinJoinApprover
from apps.bitcoin.sign_tx.bitcoin import Bitcoin
from apps.bitcoin.sign_tx.helpers import UiConfirm, UiConfirmForeignAddress
from apps.bitcoin.sign_tx.tx_info import TxInfo
from apps.common import coins


class TestApprover(TestCaseWithContext):
    def setUp(self) -> None:
        self.coin = coins.by_name("Bitcoin")
        self.fee_rate_percent = 0.3
        self.no_fee_threshold = 1000000
        self.min_registrable_amount = 5000
        self.coordinator_name = "www.example.com"

        self.node = bip32.HDNode(
            depth=0,
            fingerprint=0,
            child_num=0,
            chain_code=bytearray(32),
            private_key=b"\x01" * 32,
            curve_name="secp256k1",
        )

        self.msg_auth = AuthorizeCoinJoin(
            coordinator=self.coordinator_name,
            max_rounds=10,
            max_coordinator_fee_rate=int(self.fee_rate_percent * 10**FEE_RATE_DECIMALS),
            max_fee_per_kvbyte=7000,
            address_n=[H_(10025), H_(0), H_(0), H_(1)],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDTAPROOT,
        )
        if not utils.USE_THP:
            storage.cache_codec.start_session()

    def make_coinjoin_request(self, inputs: list[TxInput]) -> CoinJoinRequest:
        return CoinJoinRequest(
            fee_rate=int(self.fee_rate_percent * 10**FEE_RATE_DECIMALS),
            no_fee_threshold=self.no_fee_threshold,
            min_registrable_amount=self.min_registrable_amount,
            mask_public_key=bytearray(),
            signature=bytearray(),
        )

    def test_coinjoin_lots_of_inputs(self) -> None:
        denomination = 10_000_000
        coordinator_fee = int(self.fee_rate_percent / 100 * denomination)
        fees = coordinator_fee + 500

        # Other's inputs.
        inputs = [
            TxInput(
                prev_hash=bytes(32),
                prev_index=0,
                amount=denomination,
                script_pubkey=bytes(22),
                script_type=InputScriptType.EXTERNAL,
                sequence=0xFFFFFFFF,
                witness=bytes(1),
            )
            for i in range(99)
        ]

        # Our input.
        inputs.insert(
            30,
            TxInput(
                prev_hash=bytes(32),
                prev_index=0,
                address_n=[H_(10025), H_(0), H_(0), H_(1), 0, 1],
                amount=denomination,
                script_type=InputScriptType.SPENDTAPROOT,
                sequence=0xFFFFFFFF,
            ),
        )

        # Other's CoinJoined outputs.
        outputs = [
            TxOutput(
                address="",
                amount=denomination - fees,
                script_type=OutputScriptType.PAYTOTAPROOT,
                payment_req_index=0,
            )
            for i in range(99)
        ]

        # Our CoinJoined output.
        outputs.insert(
            40,
            TxOutput(
                address="",
                address_n=[H_(10025), H_(0), H_(0), H_(1), 0, 2],
                amount=denomination - fees,
                script_type=OutputScriptType.PAYTOTAPROOT,
                payment_req_index=0,
            ),
        )

        # Coordinator's output.
        outputs.append(
            TxOutput(
                address="",
                amount=coordinator_fee * len(outputs),
                script_type=OutputScriptType.PAYTOTAPROOT,
                payment_req_index=0,
            )
        )

        coinjoin_req = self.make_coinjoin_request(inputs)
        tx = SignTx(
            outputs_count=len(outputs),
            inputs_count=len(inputs),
            coin_name=self.coin.coin_name,
            lock_time=0,
            coinjoin_request=coinjoin_req,
        )
        authorization = CoinJoinAuthorization(self.msg_auth)
        approver = CoinJoinApprover(tx, self.coin, authorization)
        signer = Bitcoin(tx, None, self.coin, approver)
        tx_info = TxInfo(signer, tx)

        for txi in inputs:
            if txi.script_type == InputScriptType.EXTERNAL:
                approver.add_external_input(txi)
            else:
                await_result(approver.add_internal_input(txi, self.node))

        for txo in outputs:
            if txo.address_n:
                await_result(approver.add_change_output(txo, script_pubkey=bytes(22)))
            else:
                await_result(
                    approver.add_external_output(
                        txo, script_pubkey=bytes(22), tx_info=tx_info
                    )
                )

        await_result(approver.approve_tx(tx_info, [], None))

    def test_coinjoin_input_account_depth_mismatch(self) -> None:
        txi = TxInput(
            prev_hash=bytes(32),
            prev_index=0,
            address_n=[H_(10025), H_(0), H_(0), H_(1), 0],
            amount=10000000,
            script_type=InputScriptType.SPENDTAPROOT,
        )

        coinjoin_req = self.make_coinjoin_request([txi])
        tx = SignTx(
            outputs_count=201,
            inputs_count=100,
            coin_name=self.coin.coin_name,
            lock_time=0,
            coinjoin_request=coinjoin_req,
        )
        authorization = CoinJoinAuthorization(self.msg_auth)
        approver = CoinJoinApprover(tx, self.coin, authorization)

        with self.assertRaises(wire.ProcessError):
            await_result(approver.add_internal_input(txi, self.node))

    def test_coinjoin_input_account_path_mismatch(self) -> None:
        txi = TxInput(
            prev_hash=bytes(32),
            prev_index=0,
            address_n=[H_(10025), H_(0), H_(1), H_(1), 0, 0],
            amount=10000000,
            script_type=InputScriptType.SPENDTAPROOT,
        )

        coinjoin_req = self.make_coinjoin_request([txi])
        tx = SignTx(
            outputs_count=201,
            inputs_count=100,
            coin_name=self.coin.coin_name,
            lock_time=0,
            coinjoin_request=coinjoin_req,
        )
        authorization = CoinJoinAuthorization(self.msg_auth)
        approver = CoinJoinApprover(tx, self.coin, authorization)

        with self.assertRaises(wire.ProcessError):
            await_result(approver.add_internal_input(txi, self.node))


class TestBasicApproverForeignAddress(TestCaseWithContext):
    # BIP-44 paths, foreign for both SPENDWITNESS and SPENDTAPROOT.
    FOREIGN_A = [H_(44), H_(0), H_(0), 0, 0]
    FOREIGN_B = [H_(44), H_(0), H_(7), 0, 3]
    # BIP-86 path, valid for SPENDTAPROOT.
    NATIVE = [H_(86), H_(0), H_(0), 0, 0]

    def setUp(self) -> None:
        self.coin = coins.by_name("Bitcoin")
        self.node = bip32.HDNode(
            depth=0,
            fingerprint=0,
            child_num=0,
            chain_code=bytearray(32),
            private_key=b"\x01" * 32,
            curve_name="secp256k1",
        )
        if not utils.USE_THP:
            storage.cache_codec.start_session()

    def make_approver(self) -> BasicApprover:
        tx = SignTx(
            outputs_count=1,
            inputs_count=2,
            coin_name=self.coin.coin_name,
            lock_time=0,
        )
        return BasicApprover(tx, self.coin)

    def make_input(
        self,
        address_n: list[int],
        script_type: InputScriptType = InputScriptType.SPENDTAPROOT,
    ) -> TxInput:
        return TxInput(
            prev_hash=bytes(32),
            prev_index=0,
            amount=100000,
            script_type=script_type,
            address_n=address_n,
            sequence=0xFFFFFFFF,
        )

    def add_input(self, approver: BasicApprover, txi: TxInput) -> list[UiConfirm]:
        """Run add_internal_input(), confirming all UI requests, and return them."""
        requests: list[UiConfirm] = []
        task = approver.add_internal_input(txi, self.node)
        value = None
        while True:
            try:
                request = task.send(value)
            except StopIteration:
                return requests
            requests.append(request)
            value = True

    def test_native_path_is_not_confirmed(self) -> None:
        approver = self.make_approver()
        txi = self.make_input(self.NATIVE)
        self.assertEqual(self.add_input(approver, txi), [])
        approver.check_internal_input(txi)

    def test_each_foreign_path_is_confirmed(self) -> None:
        approver = self.make_approver()
        txi_a = self.make_input(self.FOREIGN_A)
        txi_b = self.make_input(self.FOREIGN_B)
        self.assertEqual(
            self.add_input(approver, txi_a),
            [UiConfirmForeignAddress(address_n=self.FOREIGN_A)],
        )
        self.assertEqual(
            self.add_input(approver, txi_b),
            [UiConfirmForeignAddress(address_n=self.FOREIGN_B)],
        )
        approver.check_internal_input(txi_a)
        approver.check_internal_input(txi_b)

    def test_confirmed_foreign_path_does_not_authorize_another(self) -> None:
        approver = self.make_approver()
        txi_a = self.make_input(self.FOREIGN_A)
        self.assertEqual(
            self.add_input(approver, txi_a),
            [UiConfirmForeignAddress(address_n=self.FOREIGN_A)],
        )

        approver.check_internal_input(txi_a)
        with self.assertRaises(wire.ProcessError):
            approver.check_internal_input(self.make_input(self.FOREIGN_B))

    def test_confirmed_foreign_path_does_not_authorize_another_script_type(
        self,
    ) -> None:
        approver = self.make_approver()
        txi = self.make_input(self.FOREIGN_A, InputScriptType.SPENDWITNESS)
        self.assertEqual(
            self.add_input(approver, txi),
            [UiConfirmForeignAddress(address_n=self.FOREIGN_A)],
        )

        approver.check_internal_input(txi)
        with self.assertRaises(wire.ProcessError):
            approver.check_internal_input(
                self.make_input(self.FOREIGN_A, InputScriptType.SPENDTAPROOT)
            )

    def test_native_path_does_not_authorize_a_foreign_one(self) -> None:
        approver = self.make_approver()
        txi = self.make_input(self.NATIVE)
        self.assertEqual(self.add_input(approver, txi), [])

        with self.assertRaises(wire.ProcessError):
            approver.check_internal_input(self.make_input(self.FOREIGN_A))


if __name__ == "__main__":
    unittest.main()
