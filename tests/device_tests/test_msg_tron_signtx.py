# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import pytest

from trezorlib import messages as proto, tron
from trezorlib.tools import parse_path

TRON_DEFAULT_PATH = "m/44'/195'/0'/0/0"
MNEMONIC12 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.tron,
    pytest.mark.setup_client(mnemonic=MNEMONIC12),
]


def test_tron_send_trx(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("C565"),
        ref_block_hash=bytes.fromhex("6CD623DBE83075D8"),
        expiration=1528768890000,
        timestamp=1528768831987,
        contract=proto.TronContract(
            transfer_contract=proto.TronTransferContract(
                to_address="TLrpNTBuCpGMrB9TyVwgEhNVRhtWEQPHh4", amount=1000000
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "037f02960276a50dc8327449105f59cbb3b2ca071240f7a678c4257f26df86287a58bfda988e83803ccbe8bc2d6cfeaca18f87b6c9e20ea1a77c570d5435493300"
    )


def test_tron_send_token(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("E7C3"),
        ref_block_hash=bytes.fromhex("69E2ABB19969F1E7"),
        expiration=1528997142000,
        timestamp=1528997083831,
        contract=proto.TronContract(
            transfer_asset_contract=proto.TronTransferAssetContract(
                asset_id="1002000",
                asset_name="BitTorrent",
                asset_decimals=6,
                asset_signature="304402202e2502f36b00e57be785fc79ec4043abcdd4fdd1b58d737ce123599dffad2cb602201702c307f009d014a553503b499591558b3634ceee4c054c61cedd8aca94c02b",
                to_address="TLrpNTBuCpGMrB9TyVwgEhNVRhtWEQPHh4",
                amount=1,
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "c5deb6f053ca7f9dfd9a54677cdeaee6ea084983cea62f572e60db4bdd9fbcec13b9c262fe6302ce71b291c4976a533cbecf5194c4ef5cd0d46457c822c1bb8d01"
    )


def test_tron_vote_witness(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("906E"),
        ref_block_hash=bytes.fromhex("2597B4DAC069C352"),
        expiration=1530986184000,
        timestamp=1530985887463,
        contract=proto.TronContract(
            vote_witness_contract=proto.TronVoteWitnessContract(
                votes=[
                    proto.TronVote(
                        vote_address="TKSXDA8HfE9E1y39RczVQ1ZascUEtaSToF",
                        vote_count=1000000,
                    ),
                    proto.TronVote(
                        vote_address="TTcYhypP8m4phDhN6oRexz2174zAerjEWP",
                        vote_count=100000,
                    ),
                    proto.TronVote(
                        vote_address="TE7hnUtWRRBz3SkFrX8JESWUmEvxxAhoPt",
                        vote_count=100000,
                    ),
                    proto.TronVote(
                        vote_address="TVMP5r12ymtNerq5KB4E8zAgLDmg2FqsEG",
                        vote_count=10000,
                    ),
                    proto.TronVote(
                        vote_address="TRni6NxF8CQVcywcDm67sEpCYCo7BUGXCD",
                        vote_count=1000,
                    ),
                ]
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "a35e28f7e5d887a4e90dbee56ea630d1d0b4eab0f70edde80a233895edfbde2c4e35628d11157b8a8fabd711880aaca19468f41ac9751c93dc7ec17a305aa1d801"
    )


def test_tron_witness_create(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            witness_create_contract=proto.TronWitnessCreateContract(
                url="http://cryptochain.network"
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "692859b8d668ae5146f04512ba97cf2e205b429bcf462a6fa48726be8894be81480e935a3f9d3684cf82e5378d425310066e1ea1b1d99eaebdfa58c32f0cdb8701"
    )


def test_tron_asset_issue(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("a745"),
        ref_block_hash=bytes.fromhex("5d3db33ec351b082"),
        expiration=1571828655000,
        timestamp=1571828595353,
        contract=proto.TronContract(
            asset_issue_contract=proto.TronAssetIssueContract(
                name="CryptoChain",
                abbr="CCT",
                total_supply=9999999999,
                trx_num=1000,
                num=1,
                precision=1,
                start_time=1571900000000,
                end_time=1572900000000,
                description="CryptoChain Token Issue Test",
                url="http://cryptochain.network",
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "8e5632cee4c25fa2966ef7a4a7db9df3f228ed67b23d8c4344d82d1598ec8ee55dc6b79845fd899ecce3c0310b5da2d4cf020eefbe5cdd3259bd561e1c40571601"
    )


def test_tron_witness_update(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            witness_update_contract=proto.TronWitnessUpdateContract(
                update_url="http://cryptochain.network"
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "6feca2a4558ded324f439c7cecf596f1378fbd6071569a99ea28f06c4cb1fb754720125f8721c0663e3768b7a888ee8c37fbbb9690e192b8908e225ba49a2aaa01"
    )


def test_tron_participate_asset(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            participate_asset_issue_contract=proto.TronParticipateAssetIssueContract(
                to_address="THChUb7p2bwY6ReAiJXao6qc2ZGn88T46v",
                asset_id="1000166",
                asset_name="CryptoChain",
                asset_decimals=0,
                asset_signature="30450221008417d04d1caeae31f591ae50f7d19e53e0dfb827bd51c18e66081941bf04639802203c73361a521c969e3fd7f62e62b46d61aad00e47d41e7da108546d954278a6b1",
                amount=1,
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "e58356174e071e378490acc461961694dfa3708236b9742084c21b1404b516ba205c87516e89f1b4bc63c643162d375e5f4481c7fadd608dc8e38c39c10658f100"
    )


def test_tron_account_update(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            account_update_contract=proto.TronAccountUpdateContract(
                account_name="CryptoChainTest"
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "c4c1381d3a3e23010f19f8055df6d78990fdac619ae8be030425e0de0726f4fb665618a2c663c891cb5f8b26d009d79d3650008bda429e274bf4eee3330c806a00"
    )


def test_tron_freeze_balance_bandwidth(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            freeze_balance_contract=proto.TronFreezeBalanceContract(
                frozen_balance=10000000,
                frozen_duration=3,
                resource=proto.TronResourceCode.BANDWIDTH,
            )
        ),
    )
    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "6c10c4f0149135749507607f890dc529083fe41504b22052dd68d946b4caed704a116f2d6a767934ed43ae6d4c6ccf0002317e00dfdd5415ed8c72f8c6b5f74a01"
    )


def test_tron_freeze_balance_energy(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            freeze_balance_contract=proto.TronFreezeBalanceContract(
                frozen_balance=10000000,
                frozen_duration=3,
                resource=proto.TronResourceCode.ENERGY,
            )
        ),
    )
    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "14fe46619fed9d9acf863c464854bfedd257e4072e31116f9e144b846cb112725343e0aa13cd0b856b53f2265ef2c19d9610eafee0b6c120ba501d06a4e2c49901"
    )


def test_tron_freeze_balance_bandwidth_rental(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            freeze_balance_contract=proto.TronFreezeBalanceContract(
                frozen_balance=10000000,
                frozen_duration=3,
                resource=proto.TronResourceCode.BANDWIDTH,
                receiver_address="TLrpNTBuCpGMrB9TyVwgEhNVRhtWEQPHh4",
            )
        ),
    )
    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "9885b510e3aff53b9e85511acf6b6a803a79472d5cdd27774bdc8363877e99685a9b71c2eec44de392b77bf00f6fdbab8b0a58fbee6d2401c1b2ea798a87b9a901"
    )


def test_tron_freeze_balance_energy_rental(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            freeze_balance_contract=proto.TronFreezeBalanceContract(
                frozen_balance=10000000,
                frozen_duration=3,
                resource=proto.TronResourceCode.ENERGY,
                receiver_address="TLrpNTBuCpGMrB9TyVwgEhNVRhtWEQPHh4",
            )
        ),
    )
    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "34b73c06cfb238c2ef8071e17bf1c8618cc2f14db9faef494cb9f4151631c9da33d06e2c66d78d1d3bcf4e955e8e82d7e343cc065c96d5e435d9251074433fe600"
    )


def test_tron_unfreeze_balance_bandwidth(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            unfreeze_balance_contract=proto.TronUnfreezeBalanceContract(
                resource=proto.TronResourceCode.BANDWIDTH
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "64613fa2d2b2ea18f9d37a7b97cc6c76f56c59f05b1d28806617c7b89ecc16994b275145f43a5289d49ef227f74a5cc3ac039534048416c9b3e51d82029a60e301"
    )


def test_tron_unfreeze_balance_energy(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            unfreeze_balance_contract=proto.TronUnfreezeBalanceContract(
                resource=proto.TronResourceCode.ENERGY
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "7f3f7d2f03da17c8f950bb3a606248c0a37092522b0e9ca824f44d00c6278be96e78b87c202727b9d32599118cf3f132d82b75cfdd30a02075c9c1fe0096167101"
    )


def test_tron_unfreeze_balance_bandwidth_rental(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            unfreeze_balance_contract=proto.TronUnfreezeBalanceContract(
                resource=proto.TronResourceCode.BANDWIDTH,
                receiver_address="TLrpNTBuCpGMrB9TyVwgEhNVRhtWEQPHh4",
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "90b0b27b0820ca46e6a2c42e6c80a1a7a304ec4a1859db863bad19b5db49eac3412b7015f5f637894d4ffecd88b44de8e4b2ec789b77090997b5353b17a22bfe00"
    )


def test_tron_unfreeze_balance_energy_rental(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            unfreeze_balance_contract=proto.TronUnfreezeBalanceContract(
                resource=proto.TronResourceCode.ENERGY,
                receiver_address="TLrpNTBuCpGMrB9TyVwgEhNVRhtWEQPHh4",
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "e8176724732452c7b21654922df0efc796b4ed56b2f408b0dd6ac90eb593fa9f6a67145af27e44bcfd5e515cfb6014d747ce43aec9a819eb2a4a321425dad92100"
    )


def test_tron_withdraw_balance(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            withdraw_balance_contract=proto.TronWithdrawBalanceContract()
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "1b59288fa1086c2022eca7d34a63a9cb2adc8c3e72fd49602c6e048c5ab0a44d774f42b589021b0c9d582c6c861706b877336f5d6a114cbf5dbda0ff66cdf02900"
    )


def test_tron_unfreeze_asset(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            unfreeze_asset_contract=proto.TronUnfreezeAssetContract()
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "2a5857885bb81ddb210f7a5fa1ae60e0acf9280b2bfb3a5c1463dee02e68ebce7486e11bf519c2cd6b42063ea6db919708ef9d2c8c0917636da4e7ea4518eda100"
    )


def test_tron_update_asset(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            update_asset_contract=proto.TronUpdateAssetContract(
                description="CryptoChain Token New Description",
                url="http://cryptochain.network/token",
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "d6b39a251c5dbc0684672d4850c08eec9e5d1df2a9848e01d2b195e00962258651765bc314a5bd56b98aa91da70dfbbdc71526eef3cbf7c62878e541793bddba00"
    )


def test_tron_proposal_create_contract(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            proposal_create_contract=proto.TronProposalCreateContract(
                parameters=[
                    proto.TronProposalParameters(key=0, value=36000000),
                    proto.TronProposalParameters(key=6, value=300000000000),
                    proto.TronProposalParameters(key=4, value=5000000000),
                ]
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "648d96f3a33ba90c5b3333c54d56fff2b81a70c80567aafe4eab092c1c1c09ff0b7724039a6f16a937f6bf1fa2dbb0c9843e1cbec63aeb8805141128b36d001301"
    )


def test_tron_proposal_approve_contract(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            proposal_approve_contract=proto.TronProposalApproveContract(
                proposal_id=10000, is_add_approval=False
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "a6cdfed4863d3f4d6adfba1444e47b277026d35d52988f223d2bed5eaa979c266ab74e7212df24f0f058661522bec05419ccfb28321c646632a8c502f06dda9e00"
    )


def test_tron_proposal_delete_contract(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            proposal_delete_contract=proto.TronProposalApproveContract(
                proposal_id=10000
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "636577a6800c6ab4e7c11a72d5f0b3d865e190b51714cf5c4bd1d71bc37f54643582382314c236b489376bc4ab5d0612e3c6f9434e97db6dd41c517757cc8d7101"
    )


def test_tron_set_account_id_contract(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("D0EF"),
        ref_block_hash=bytes.fromhex("6CD6025AFD991D7D"),
        expiration=1531429101000,
        timestamp=1531428803023,
        contract=proto.TronContract(
            set_account_id=proto.TronSetAccountIdContract(account_id="CryptoChain")
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "d3868f17951ff242ab92c2be500c676d21f9d396c0c8ab82912975d593bf3f0279ebbd9b7211d1f4ed3c2e2045d62ccade2f48455fadd12023397acb515644d000"
    )


def test_tron_create_exchange_contract(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("b80e"),
        ref_block_hash=bytes.fromhex("2b264690d8bd9711"),
        expiration=1561994163000,
        timestamp=1561994105137,
        contract=proto.TronContract(
            exchange_create_contract=proto.TronExchangeCreateContract(
                first_asset_id="1002000",
                first_asset_name="BitTorrent",
                first_asset_decimals=6,
                first_asset_signature="304402202e2502f36b00e57be785fc79ec4043abcdd4fdd1b58d737ce123599dffad2cb602201702c307f009d014a553503b499591558b3634ceee4c054c61cedd8aca94c02b",
                first_asset_balance=1000000000,
                second_asset_id="_",
                second_asset_name="TRX",
                second_asset_decimals=6,
                second_asset_signature="3044022037c53ecb06abe1bfd708bd7afd047720b72e2bfc0a2e4b6ade9a33ae813565a802200a7d5086dc08c4a6f866aad803ac7438942c3c0a6371adcb6992db94487f66c7",
                second_asset_balance=100000000000,
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "c4fe8e85c96fe5a847e8db67ca00d39f3859fdcd970373c925a1afe93099d4d507f14d97b653488c192cb5bd7c903b1f5968605e2a5adfd071433ff542afc05201"
    )


def test_tron_exchange_inject_contract(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("b80e"),
        ref_block_hash=bytes.fromhex("2b264690d8bd9711"),
        expiration=1561994163000,
        timestamp=1561994105137,
        contract=proto.TronContract(
            exchange_inject_contract=proto.TronExchangeInjectContract(
                exchange_id=6,
                token_id="1000166",
                quant=10000,
                first_asset_id="1000166",
                first_asset_name="CryptoChain",
                first_asset_decimals=0,
                second_asset_id="_",
                second_asset_name="TRX",
                second_asset_decimals=6,
                exchange_signature="3045022100fe276f30a63173b2440991affbbdc5d6d2d22b61b306b24e535a2fb866518d9c02205f7f41254201131382ec6c8b3c78276a2bb136f910b9a1f37bfde192fc448793",
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "2fd95947864b04812d3523997a4cf911ad1d7dd25940346530007db8dcd975976eff84f8cad6321b5f1c9b399b1d89a22e66e6e71b13439a66b7df3fbc6b588000"
    )


def test_tron_exchange_withdraw_contract(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("b80e"),
        ref_block_hash=bytes.fromhex("2b264690d8bd9711"),
        expiration=1561994163000,
        timestamp=1561994105137,
        contract=proto.TronContract(
            exchange_withdraw_contract=proto.TronExchangeWithdrawContract(
                exchange_id=6,
                token_id="1000166",
                quant=10000,
                first_asset_id="1000166",
                first_asset_name="CryptoChain",
                first_asset_decimals=0,
                second_asset_id="_",
                second_asset_name="TRX",
                second_asset_decimals=6,
                exchange_signature="3045022100fe276f30a63173b2440991affbbdc5d6d2d22b61b306b24e535a2fb866518d9c02205f7f41254201131382ec6c8b3c78276a2bb136f910b9a1f37bfde192fc448793",
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "0b357a4760dc29bb6b4e3f2d5ef437de070f09df7b46f57592db9c7a6823f2411f7e2264ed13126b8ed003e8b03794b3a0ec27f7841d758349714f34d1ebcf7b00"
    )


def test_tron_exchange_transaction_contract(client):

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("b80e"),
        ref_block_hash=bytes.fromhex("2b264690d8bd9711"),
        expiration=1561994163000,
        timestamp=1561994105137,
        contract=proto.TronContract(
            exchange_transaction_contract=proto.TronExchangeTransactionContract(
                exchange_id=6,
                token_id="1000166",
                quant=10000,
                expected=10000000,
                first_asset_id="1000166",
                first_asset_name="CryptoChain",
                first_asset_decimals=0,
                second_asset_id="_",
                second_asset_name="TRX",
                second_asset_decimals=6,
                exchange_signature="3045022100fe276f30a63173b2440991affbbdc5d6d2d22b61b306b24e535a2fb866518d9c02205f7f41254201131382ec6c8b3c78276a2bb136f910b9a1f37bfde192fc448793",
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "ae01e592cf9da33a2bea2db24a821d51b91c641f15141b45b49e31739e6c296439a19fbe1839e95d110df66bae9001b965371041c3465e497f17ce0484bd0af800"
    )


def test_tron_transfer_trc20(client):
    data = bytearray()
    # method id signalizing `transfer(address _to, uint256 _value)` function
    data.extend(bytes.fromhex("a9059cbb"))
    # 1st function argument (to - the receiver)
    data.extend(
        bytes.fromhex(
            "000000000000000000000000f1f43b97e403929a6ccce5150cbcc7baf9ee91a0"
        )
    )
    # 2nd function argument (value - amount to be transferred)
    data.extend(
        bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000002ebae40"
        )
    )

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("f89b"),
        ref_block_hash=bytes.fromhex("5f0ff66bec893fab"),
        expiration=1574675991000,
        timestamp=1574675932727,
        fee_limit=10000000,
        contract=proto.TronContract(
            trigger_smart_contract=proto.TronTriggerSmartContract(
                contract_address="TBoTZcARzWVgnNuB9SyE3S5g1RwsXoQL16", data=data
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "6eb52e1a61c72e3c1e8b253322fbeae41beb16830443cdeea7114a240b91651208a87d9775172d68d3077e942d0b4c5916f8741cd83ac8c258eb69eab65cb84f00"
    )


def test_tron_approve_trc20(client):
    data = bytearray()
    # method id signalizing `transfer(address _to, uint256 _value)` function
    data.extend(bytes.fromhex("095ea7b3"))
    # 1st function argument (to - the receiver)
    data.extend(
        bytes.fromhex(
            "000000000000000000000000f1f43b97e403929a6ccce5150cbcc7baf9ee91a0"
        )
    )
    # 2nd function argument (value - amount to be transferred)
    data.extend(
        bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000002ebae40"
        )
    )

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("f89b"),
        ref_block_hash=bytes.fromhex("5f0ff66bec893fab"),
        expiration=1574675991000,
        timestamp=1574675932727,
        fee_limit=10000000,
        contract=proto.TronContract(
            trigger_smart_contract=proto.TronTriggerSmartContract(
                contract_address="TBoTZcARzWVgnNuB9SyE3S5g1RwsXoQL16", data=data
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "8610da2a2217448880f8f61723da993070f365e3e23fdff9b565cd23cefb860d4d877a5a79552de905258b8646e1c816af8a293af7aadc37f5a1445b332b1ba200"
    )


def test_tron_transfer_trc20_not_in_list(client):
    data = bytearray()
    # method id signalizing `transfer(address _to, uint256 _value)` function
    data.extend(bytes.fromhex("a9059cbb"))
    # 1st function argument (to - the receiver)
    data.extend(
        bytes.fromhex(
            "000000000000000000000000f1f43b97e403929a6ccce5150cbcc7baf9ee91a0"
        )
    )
    # 2nd function argument (value - amount to be transferred)
    data.extend(
        bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000002ebae40"
        )
    )

    msg = proto.TronSignTx(
        ref_block_bytes=bytes.fromhex("f89b"),
        ref_block_hash=bytes.fromhex("5f0ff66bec893fab"),
        expiration=1574675991000,
        timestamp=1574675932727,
        fee_limit=10000000,
        contract=proto.TronContract(
            trigger_smart_contract=proto.TronTriggerSmartContract(
                contract_address="TKYTRRRkyEHKLeDpGmT9TCeqxxnH2XoEBP", data=data
            )
        ),
    )

    result = tron.sign_tx(client, parse_path(TRON_DEFAULT_PATH), msg)
    assert (
        result.signature.hex()
        == "ffc2d8e8f6297194f30d3c4af37bb47e956ab28025d601e472cae3bbfba75ab834d2197f46c9c9a71df65b3388357ba72ee3a45af17a1f48eadc80b75f0d572000"
    )
