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

from trezorlib import btc, messages
from trezorlib.tools import btc_hash, parse_path

from ...tx_cache import TxCache

TX_API = TxCache("Firo Testnet")
TXHASH_8a34cc = bytes.fromhex(
    "8a34ccceaf138fd14398303340afb37871cb0ea6719ceba315172edb9ff6d625"
)


@pytest.mark.altcoin
def test_spend_lelantus(client):
    inp1 = messages.TxInputType(
        # THgGLVqfzJcaxRVPWE5fd8YJ1GpVePq2Uk
        address_n=parse_path("m/44'/1'/0'/0/4"),
        amount=1_000_000_000,
        prev_hash=TXHASH_8a34cc,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        # m/44'/1'/0'/0/5
        address="TPypFKi3aziXmiH1MiwagaK71apv5XARGY",
        amount=1_000_000_000 - 1_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    _, serialized_tx = btc.sign_tx(
        client, "Firo Testnet", [inp1], [out1], prev_txes=TX_API
    )
    assert (
        serialized_tx.hex()
        == "010000000125d6f69fdb2e1715a3eb9c71a60ecb7178b3af4033309843d18f13afcecc348a000000006a47304402207b490135583a2ac6650806c706dfd15954f9ac85b64a75d7264653e4b1cd4e29022052946b28f97a415bd0b2b02c3a71ac8cb26f9a9387ac82856b4c7116848d090c01210313a443e806f25052ac7363adc689fcfa72893f2a51a35ab5e096ed5e6cd8517effffffff0118c69a3b000000001976a91499af2ecbf5892079e0297c59b91981b067da36a988ac00000000"
    )
    # accepted by network: https://testblockbook.firo.org/tx/866bc7041989ad038e5b38b7577325d015b67238ea9387cde6ba837fff4a61be
    assert (
        btc_hash(serialized_tx)[::-1].hex()
        == "866bc7041989ad038e5b38b7577325d015b67238ea9387cde6ba837fff4a61be"
    )
