from common import H_, await_result, unittest  # isort:skip

import storage.cache
from trezor import wire
from trezor.crypto import bip32
from trezor.crypto.curve import bip340, secp256k1
from trezor.crypto.hashlib import sha256
from trezor.enums import InputScriptType, OutputScriptType
from trezor.messages import (
    AuthorizeCoinJoin,
    CoinJoinRequest,
    SignTx,
    TxInput,
    TxOutput,
)
from trezor.utils import HashWriter

from apps.bitcoin import writers
from apps.bitcoin.authorization import FEE_RATE_DECIMALS, CoinJoinAuthorization
from apps.bitcoin.sign_tx.approvers import CoinJoinApprover
from apps.bitcoin.sign_tx.bitcoin import Bitcoin
from apps.bitcoin.sign_tx.tx_info import TxInfo
from apps.common import coins


class TestApprover(unittest.TestCase):
    def setUp(self):
        self.coin = coins.by_name("Bitcoin")
        self.fee_rate_percent = 0.3
        self.no_fee_threshold = 1000000
        self.min_registrable_amount = 5000
        self.coordinator_name = "www.example.com"

        # Private key for signing and masking CoinJoin requests.
        # m/0h for "all all ... all" seed.
        self.private_key = b"?S\ti\x8b\xc5o{,\xab\x03\x194\xea\xa8[_:\xeb\xdf\xce\xef\xe50\xf17D\x98`\xb9dj"

        self.node = bip32.HDNode(
            depth=0,
            fingerprint=0,
            child_num=0,
            chain_code=bytearray(32),
            private_key=b"\x01" * 32,
            curve_name="secp256k1",
        )
        self.tweaked_node_pubkey = b"\x02" + bip340.tweak_public_key(
            self.node.public_key()[1:]
        )

        self.msg_auth = AuthorizeCoinJoin(
            coordinator=self.coordinator_name,
            max_rounds=10,
            max_coordinator_fee_rate=int(
                self.fee_rate_percent * 10**FEE_RATE_DECIMALS
            ),
            max_fee_per_kvbyte=7000,
            address_n=[H_(10025), H_(0), H_(0), H_(1)],
            coin_name=self.coin.coin_name,
            script_type=InputScriptType.SPENDTAPROOT,
        )
        storage.cache.start_session()

    def make_coinjoin_request(self, inputs):
        mask_public_key = secp256k1.publickey(self.private_key)
        coinjoin_flags = bytearray()
        for txi in inputs:
            shared_secret = secp256k1.multiply(
                self.private_key, self.tweaked_node_pubkey
            )[1:33]
            h_mask = HashWriter(sha256())
            writers.write_bytes_fixed(h_mask, shared_secret, 32)
            writers.write_bytes_reversed(h_mask, txi.prev_hash, writers.TX_HASH_SIZE)
            writers.write_uint32(h_mask, txi.prev_index)
            mask = h_mask.get_digest()[0] & 1
            signable = txi.script_type == InputScriptType.SPENDTAPROOT
            txi.coinjoin_flags = signable ^ mask
            coinjoin_flags.append(txi.coinjoin_flags)

        # Compute CoinJoin request signature.
        h_request = HashWriter(sha256(b"CJR1"))
        writers.write_bytes_prefixed(h_request, self.coordinator_name.encode())
        writers.write_uint32(h_request, self.coin.slip44)
        writers.write_uint32(
            h_request, int(self.fee_rate_percent * 10**FEE_RATE_DECIMALS)
        )
        writers.write_uint64(h_request, self.no_fee_threshold)
        writers.write_uint64(h_request, self.min_registrable_amount)
        writers.write_bytes_fixed(h_request, mask_public_key, 33)
        writers.write_bytes_prefixed(h_request, coinjoin_flags)
        writers.write_bytes_fixed(h_request, sha256().digest(), 32)
        writers.write_bytes_fixed(h_request, sha256().digest(), 32)
        signature = secp256k1.sign(self.private_key, h_request.get_digest())

        return CoinJoinRequest(
            fee_rate=int(self.fee_rate_percent * 10**FEE_RATE_DECIMALS),
            no_fee_threshold=self.no_fee_threshold,
            min_registrable_amount=self.min_registrable_amount,
            mask_public_key=mask_public_key,
            signature=signature,
        )

    def test_coinjoin_lots_of_inputs(self):
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
                witness="",
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

        for txi in inputs:
            if txi.script_type == InputScriptType.EXTERNAL:
                approver.add_external_input(txi)
            else:
                await_result(approver.add_internal_input(txi, self.node))

        for txo in outputs:
            if txo.address_n:
                await_result(approver.add_change_output(txo, script_pubkey=bytes(22)))
            else:
                await_result(approver.add_external_output(txo, script_pubkey=bytes(22)))

        await_result(approver.approve_tx(TxInfo(signer, tx), []))

    def test_coinjoin_input_account_depth_mismatch(self):
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

    def test_coinjoin_input_account_path_mismatch(self):
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


if __name__ == "__main__":
    unittest.main()
