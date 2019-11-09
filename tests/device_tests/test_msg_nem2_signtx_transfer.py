# # This file is part of the Trezor project.
# #
# # Copyright (C) 2012-2019 SatoshiLabs and contributors
# #
# # This library is free software: you can redistribute it and/or modify
# # it under the terms of the GNU Lesser General Public License version 3
# # as published by the Free Software Foundation.
# #
# # This library is distributed in the hope that it will be useful,
# # but WITHOUT ANY WARRANTY; without even the implied warranty of
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# # GNU Lesser General Public License for more details.
# #
# # You should have received a copy of the License along with this library.
# # If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

# import pytest

# from trezorlib import messages as proto, nem2
# from trezorlib.tools import parse_path

# from ..common import MNEMONIC12

# @pytest.mark.altcoin
# @pytest.mark.nem2
# class TestMsgNEM2SignTxTransfer:
#     @pytest.mark.setup_client(mnemonic=MNEMONIC12)
#     def test_nem2_signtx_simple(self, client):
#         with client:
#             client.set_expected_responses(
#                 [
#                     # Confirm transfer and network fee
#                     proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
#                     # Confirm recipient
#                     proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
#                     proto.NEM2SignedTx(),
#                 ]
#             )

#             tx = nem2.sign_tx(
#                 client,
#                 parse_path("m/44'/43'/0'"),
#                 {
#                     "type": nem2.TYPE_TRANSACTION_TRANSFER,
#                     "network_type": nem2.NETWORK_TYPE_TEST_NET,
#                     "generation_hash": "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
#                     "version": 36865,
#                     "max_fee": 100,
#                     "deadline": 113212179217,
#                     "recipient_address": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
#                     "mosaics": [{ "amount": 10000000, "id": "85BBEA6CC462B244" }],
#                     "message": {
#                         "payload": b"test_nem2_transaction_transfer".hex(),
#                         "type": 1,
#                     },
#                 },
#             )

#             assert (
#                 tx.payload.hex()
#                 == "B70000007BC55B27E1BA92994B021342176E4C274A2DC74C9A1F724EC39BF5E8D0C28ED066E4CD762B8A98C38081AF347D20DAE0140DCAF19C3E67896C164AF6CB8C7A0F8AF53BB8F3A167C68F264C33237DB309DBC88F64D7A1088B8BEEA5A34DBBBEC201985441640000000000000071A2155C1A00000098168113466037C15CE3FDD698777E6B3B46AA079BA2D6CF4913000100546869732069732061207472616E7366657244B262C46CEABB858096980000000000"
#             )
#             assert (
#                 tx.hash.hex()
#                 == "76287219944D387336C27626CB0902B141B66032B99893E687837C85B160E56A"
#             )
