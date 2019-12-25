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

# XDR decoding tool available at:
#   https://www.stellar.org/laboratory/#xdr-viewer
#
# ## Test Info
#
# The default mnemonic generates the following Stellar keypair at path 44'/148'/0':
#   GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW
#   SDE2YU4V2IYSJIUH7MONDYZTSSLDXV5QDEGUUOLCU4TK7CZWTAXZ5CEG
#
# ### Testing a new Operation
#
# 1. Start at the Stellar transaction builder: https://www.stellar.org/laboratory/#txbuilder?network=test
#   (Verify that the "test" network is active in the upper right)
#
# 2. Fill out the fields at the top as follows:
#   Source account: GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW
#   Transaction sequence number: 4294967296 (see _create_msg)
#   Base fee: 100
#   Memo: None
#   Time Bounds: <leave blank>
#
# 3. Select the operation to test, such as Create Account
#
# 4. Fill out the fields for the operation
#
# 5. Scroll down to the bottom of the page and click "Sign in Transaction Signer"
#
# 6. In the first "Add Signer" text box enter the secret key: SDE2YU4V2IYSJIUH7MONDYZTSSLDXV5QDEGUUOLCU4TK7CZWTAXZ5CEG
#
# 7. Scroll down to the signed XDR blob and click "View in XDR Viewer"
#
# 8. Scroll down to the bottom and look at the "signatures" section. The Trezor should generate the same signature
#

from base64 import b64encode

import pytest

from trezorlib import messages, stellar
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.stellar,
    pytest.mark.setup_client(mnemonic=MNEMONIC12),
]

ADDRESS_N = parse_path(stellar.DEFAULT_BIP32_PATH)
NETWORK_PASSPHRASE = "Test SDF Network ; September 2015"


def _create_msg() -> messages.StellarSignTx:
    return messages.StellarSignTx(
        source_account="GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW",
        fee=100,
        sequence_number=0x100000000,
        memo_type=0,
    )


def test_sign_tx_bump_sequence_op(client):
    op = messages.StellarBumpSequenceOp()
    op.bump_to = 0x7FFFFFFFFFFFFFFF
    tx = _create_msg()

    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)
    assert (
        b64encode(response.signature)
        == b"ZMIfHWhpyXdg40PzwOtkcXYnbZIO12Qy0WvkGqoYpb7jyWbG2HQCG7dgWhCoU5K81pvZTA2pMwiPjMwCXA//Bg=="
        # 64c21f1d6869c97760e343f3c0eb647176276d920ed76432d16be41aaa18a5bee3c966c6d874021bb7605a10a85392bcd69bd94c0da933088f8ccc025c0fff06
    )


def test_sign_tx_account_merge_op(client):
    op = messages.StellarAccountMergeOp()
    op.destination_account = "GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"

    tx = _create_msg()

    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)

    assert (
        response.public_key.hex()
        == "15d648bfe4d36f196cfb5735ffd8ca54cd4b8233f743f22449de7cf301cdb469"
    )
    assert (
        b64encode(response.signature)
        == b"2R3Pj89U+dWrqy7otUrLLjtANjAg0lmBQL8E+89Po0Y94oqZkauP8j3WE7+/z7vF6XvAMLoOdqRYkUzr2oh7Dg=="
        # d91dcf8fcf54f9d5abab2ee8b54acb2e3b40363020d2598140bf04fbcf4fa3463de28a9991ab8ff23dd613bfbfcfbbc5e97bc030ba0e76a458914cebda887b0e
    )


def test_sign_tx_create_account_op(client):
    """Create new account with initial balance of 100.0333"""

    op = messages.StellarCreateAccountOp()
    op.new_account = "GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"
    op.starting_balance = 1000333000

    tx = _create_msg()

    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)

    assert (
        b64encode(response.signature)
        == b"vrRYqkM4b54NrDR05UrW7ZHU7CNcidV0fn+bk9dqOW1bCbmX3YfeRbk2Tf1aea8nr9SD0sfBhtrDpdyxUenjBw=="
        # beb458aa43386f9e0dac3474e54ad6ed91d4ec235c89d5747e7f9b93d76a396d5b09b997dd87de45b9364dfd5a79af27afd483d2c7c186dac3a5dcb151e9e307
    )


def test_sign_tx_payment_op_native(client):
    """Native payment of 50.0111 XLM to GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"""

    op = messages.StellarPaymentOp()
    op.amount = 500111000
    op.destination_account = "GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"

    tx = _create_msg()

    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)

    assert (
        b64encode(response.signature)
        == b"pDc6ghKCLNoYbt3h4eBw+533237m0BB0Jp/d/TxJCA83mF3o5Fr4l5vwAWBR62hdTWAP9MhVluY0cd5i54UwDg=="
        # a4373a8212822cda186edde1e1e070fb9df7db7ee6d01074269fddfd3c49080f37985de8e45af8979bf0016051eb685d4d600ff4c85596e63471de62e785300e
    )


def test_sign_tx_payment_op_native_explicit_asset(client):
    """Native payment of 50.0111 XLM to GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"""

    op = messages.StellarPaymentOp()
    op.amount = 500111000
    op.destination_account = "GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"
    op.asset = messages.StellarAssetType(0)

    tx = _create_msg()

    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)

    assert (
        b64encode(response.signature)
        == b"pDc6ghKCLNoYbt3h4eBw+533237m0BB0Jp/d/TxJCA83mF3o5Fr4l5vwAWBR62hdTWAP9MhVluY0cd5i54UwDg=="
        # a4373a8212822cda186edde1e1e070fb9df7db7ee6d01074269fddfd3c49080f37985de8e45af8979bf0016051eb685d4d600ff4c85596e63471de62e785300e
    )


def test_sign_tx_payment_op_custom_asset1(client):
    """Custom asset payment (code length 1) of 50.0111 X to GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"""

    op = messages.StellarPaymentOp()
    op.amount = 500111000
    op.destination_account = "GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"

    op.asset = messages.StellarAssetType(
        1, "X", "GAUYJFQCYIHFQNS7CI6BFWD2DSSFKDIQZUQ3BLQODDKE4PSW7VVBKENC"
    )
    tx = _create_msg()

    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)

    assert (
        b64encode(response.signature)
        == b"ArZydOtXU2whoRuSjJLFIWPSIsq3AbsncJZ+THF24CRSriVWw5Fy/dHrDlUOu4fzU28I6osDMeI39aWezg5tDw=="
        # 02b67274eb57536c21a11b928c92c52163d222cab701bb2770967e4c7176e02452ae2556c39172fdd1eb0e550ebb87f3536f08ea8b0331e237f5a59ece0e6d0f
    )


def test_sign_tx_payment_op_custom_asset12(client):
    """Custom asset payment (code length 12) of 50.0111 ABCDEFGHIJKL to GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"""

    op = messages.StellarPaymentOp()
    op.amount = 500111000
    op.destination_account = "GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V"

    op.asset = messages.StellarAssetType(
        2, "ABCDEFGHIJKL", "GAUYJFQCYIHFQNS7CI6BFWD2DSSFKDIQZUQ3BLQODDKE4PSW7VVBKENC"
    )
    tx = _create_msg()

    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)

    assert (
        b64encode(response.signature)
        == b"QZIP4XKPfe4OpZtuJiyrMZBX9YBzvGpHGcngdgFfHn2kcdONreF384/pCF80xfEnGm8grKaoOnUEKxqcMKvxAA=="
        # 41920fe1728f7dee0ea59b6e262cab319057f58073bc6a4719c9e076015f1e7da471d38dade177f38fe9085f34c5f1271a6f20aca6a83a75042b1a9c30abf100
    )


def test_sign_tx_set_options(client):
    """Set inflation destination"""

    op = messages.StellarSetOptionsOp()
    op.inflation_destination_account = (
        "GAFXTC5OV5XQD66T7WGOB2HUVUC3ZVJDJMBDPTVQYV3G3K7TUHC6CLBR"
    )

    tx = _create_msg()
    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)

    assert (
        b64encode(response.signature)
        == b"dveWhKY8x7b0YqGHWH6Fo1SskxaHP11NXd2n6oHKGiv+T/LqB+CCzbmJA0tplZ+0HNPJbHD7L3Bsg/y462qLDA=="
        # 76f79684a63cc7b6f462a187587e85a354ac9316873f5d4d5ddda7ea81ca1a2bfe4ff2ea07e082cdb989034b69959fb41cd3c96c70fb2f706c83fcb8eb6a8b0c
    )

    op = messages.StellarSetOptionsOp()
    op.signer_type = 0
    op.signer_key = bytes.fromhex(
        "72187adb879c414346d77c71af8cce7b6eaa57b528e999fd91feae6b6418628e"
    )
    op.signer_weight = 2

    tx = _create_msg()
    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)
    assert (
        b64encode(response.signature)
        == b"EAeihuFBhUnjH6Sgd/+uAHlvajfv944VEpNSCLsOULNxYWdo/S0lJdUZw/2kN6I+ztKL7ZPQ5gYPJRNUePTOCg=="
        # 1007a286e1418549e31fa4a077ffae00796f6a37eff78e1512935208bb0e50b371616768fd2d2525d519c3fda437a23eced28bed93d0e6060f25135478f4ce0a
    )

    op = messages.StellarSetOptionsOp()
    op.medium_threshold = 0

    tx = _create_msg()
    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)
    assert (
        b64encode(response.signature)
        == b"E2pz06PFB5CvIT3peUcY0wxo7u9da2h6/+/qim1eRWLHC73ZtFqDtLMBaKnr63ZfjB/kDzZmCzHxiv5m+m6+AQ=="
        # 136a73d3a3c50790af213de9794718d30c68eeef5d6b687affefea8a6d5e4562c70bbdd9b45a83b4b30168a9ebeb765f8c1fe40f36660b31f18afe66fa6ebe01
    )

    op = messages.StellarSetOptionsOp()
    op.low_threshold = 0
    op.high_threshold = 3
    op.clear_flags = 0

    tx = _create_msg()
    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)
    assert (
        b64encode(response.signature)
        == b"ySQE4aS0TI+N1xjSwi/pABHpC+A6RrNPWDOuFYGJFQ5B4vIU2S+ql2gCGLE7bQiYZ5dK9021f+a30mZoYeFLDw=="
        # c92404e1a4b44c8f8dd718d2c22fe90011e90be03a46b34f5833ae158189150e41e2f214d92faa97680218b13b6d089867974af74db57fe6b7d2666861e14b0f
    )

    op = messages.StellarSetOptionsOp()
    op.set_flags = 3
    op.master_weight = 4
    op.home_domain = "hello"

    tx = _create_msg()
    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)
    assert (
        b64encode(response.signature)
        == b"22rfcOrxBiE5akpNsnWX8yPgAOpclbajVqXUaXMNeL000p1OhFhi050t1+GNRpoSNyfVsJGNvtlICGpH4ksDAQ=="
        # db6adf70eaf10621396a4a4db27597f323e000ea5c95b6a356a5d469730d78bd34d29d4e845862d39d2dd7e18d469a123727d5b0918dbed948086a47e24b0301
    )


def test_sign_tx_timebounds(client):
    op = messages.StellarSetOptionsOp()
    tx = _create_msg()
    tx.timebounds_start = 1577836800
    tx.timebounds_end = 1577839000
    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)
    assert (
        b64encode(response.signature)
        == b"KkZSQxXxEwfeGuFEHD7e93hei34rwK7VB79udYzileg6P/QEzK+lKyB9blUy+dPV3e7PvlHMj1FKXOsrgj/uCA=="
        # 2a46524315f11307de1ae1441c3edef7785e8b7e2bc0aed507bf6e758ce295e83a3ff404ccafa52b207d6e5532f9d3d5ddeecfbe51cc8f514a5ceb2b823fee08
    )

    tx.timebounds_start = 100
    tx.timebounds_end = None
    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)
    assert (
        b64encode(response.signature)
        == b"ukpdaMwe6wdNnbVnOl0ZDvU1dde7Mtnjzy2IhjeZAjk8Ze+52WCv4M8IFjLoNF5c0aB847XYozFj8AsZ/k5fDQ=="
        # ba4a5d68cc1eeb074d9db5673a5d190ef53575d7bb32d9e3cf2d8886379902393c65efb9d960afe0cf081632e8345e5cd1a07ce3b5d8a33163f00b19fe4e5f0d
    )

    tx.timebounds_start = None
    tx.timebounds_end = 111111111
    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)
    assert (
        b64encode(response.signature)
        == b"9sFE/EC+zYlYC2t7R33HsI540nOmJi/aHruu2qG+RW4FEvhKLybLS5pRRhSb0IP3comcv1Q3e2Glvis6PgVICQ=="
        # f6c144fc40becd89580b6b7b477dc7b08e78d273a6262fda1ebbaedaa1be456e0512f84a2f26cb4b9a5146149bd083f772899cbf54377b61a5be2b3a3e054809
    )


def test_manage_data(client):
    tx = _create_msg()

    # testing a value whose length is not divisible by 4
    op = messages.StellarManageDataOp(key="data", value=b"abc")

    response = stellar.sign_tx(client, tx, [op], ADDRESS_N, NETWORK_PASSPHRASE)
    assert (
        b64encode(response.signature)
        == b"MTa8fmhM7BxYYo9kY1RKQFFrg/MVfzsgiPSuP7+SJZjhQ3P1ucN5JUnfmD5484ULRPjVTd+0YYjS6hScLupbCQ=="
        # 3136bc7e684cec1c58628f6463544a40516b83f3157f3b2088f4ae3fbf922598e14373f5b9c3792549df983e78f3850b44f8d54ddfb46188d2ea149c2eea5b09
    )
