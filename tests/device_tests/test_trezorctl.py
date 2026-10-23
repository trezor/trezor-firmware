# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from trezorlib import btc, messages, protobuf
from trezorlib.cli.trezorctl import cli
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.tools import parse_path
from trezorlib.transport.udp import UdpTransport

from ..tx_cache import TxCache

# trezorctl has no way to answer the THP pairing code prompt here
pytestmark = pytest.mark.models(skip="eckhart", reason="trezorctl needs THP pairing")

PATH = "m/84h/0h/0h/0/0"

TXHASH_b36780 = "b36780ceb86807ca6e7535a6fd418b1b788cb9b227d2c8a26a0de295e523219e"
# same transaction as test_signtx_segwit_native.py::test_send_native
SIGNED_TX = (
    "010000000001019e2123e595e20d6aa2c8d227b2b98c781b8b41fda635756eca0768b8ce8067b3"
    "0000000000ffffffff02409c00000000000017a9147a55d61848e77ca266e79a39bfc85c580a64"
    "26c98750c3000000000000160014cd4ee15090b177f15ed0760d85956d93b5990d5f0247304402"
    "200c734ed16a9226162a29133c14fad3565332c60346050ceb9246e73a2fc8485002203463d40c"
    "f78eb5cc9718d6617d9f251b987e96cb58525795a507acb9b91696c7012103f60fc56bf7b53265"
    "37c7e86e0a63b6cd008eeb87d39af324cee5bcc3424bf4d000000000"
)


@pytest.fixture
def path(client: Client) -> str:
    # trezorctl opens a second connection to the device
    if not isinstance(client.transport, UdpTransport):
        pytest.skip("trezorctl tests run on the emulator only")
    return client.transport.get_path()


def trezorctl(path: str, *args: str) -> Result:
    return CliRunner().invoke(cli, ["-p", path, *args], catch_exceptions=False)


def trezorctl_confirm(client: Client, path: str, *args: str) -> Result:
    """Run trezorctl and confirm every screen on the device until it exits."""
    with ThreadPoolExecutor(1) as pool:
        result = pool.submit(trezorctl, path, *args)
        while not result.done():
            client.debug.press_yes()
            time.sleep(0.3)
        return result.result()


def expected_address(session: Session) -> str:
    # must run before trezorctl, which opens its own session
    return btc.get_address(
        session,
        "Bitcoin",
        parse_path(PATH),
        script_type=messages.InputScriptType.SPENDWITNESS,
    )


def test_get_features(session: Session, path: str):
    result = trezorctl(path, "get-features")
    assert result.exit_code == 0, result.output
    assert "initialized: True" in result.output


def test_btc_get_address(session: Session, path: str):
    expected = expected_address(session)
    result = trezorctl(path, "btc", "get-address", "-n", PATH)
    assert result.exit_code == 0, result.output
    assert result.output.strip() == expected


@pytest.mark.setup_client(passphrase="TREZOR")
def test_get_session(
    client: Client, session: Session, path: str, monkeypatch: pytest.MonkeyPatch
):
    expected = expected_address(session)
    monkeypatch.setenv("PASSPHRASE", "TREZOR")
    result = trezorctl_confirm(client, path, "--passphrase-on-host", "get-session")
    assert result.exit_code == 0, result.output
    session_id = result.output.splitlines()[-1]

    # with no passphrase available, only the resumed session can answer
    monkeypatch.delenv("PASSPHRASE")
    get_address = ("--passphrase-on-host", "btc", "get-address", "-n", PATH)
    result = trezorctl(path, "-s", session_id, *get_address)
    assert result.exit_code == 0, result.output
    assert result.output.strip() == expected

    # an empty -s overrides a TREZOR_SESSION_ID from the environment
    result = trezorctl(path, "-s", "", *get_address)
    assert result.exit_code != 0, result.output


def test_btc_sign_message(client: Client, session: Session, path: str):
    expected = expected_address(session)
    result = trezorctl_confirm(client, path, "btc", "sign-message", "-n", PATH, "hello")
    assert result.exit_code == 0, result.output
    assert f"address: {expected}" in result.output

    signature = result.output.split("signature: ")[1].strip()
    result = trezorctl_confirm(
        client, path, "btc", "verify-message", expected, signature, "hello"
    )
    assert result.exit_code == 0, result.output
    assert result.output.splitlines()[-1] == "True"


def test_btc_sign_tx(client: Client, session: Session, path: str, tmp_path: Path):
    prev_tx = TxCache("Testnet").get_tx(TXHASH_b36780)
    tx = {
        "coin_name": "Testnet",
        "inputs": [
            {
                "address_n": parse_path("m/84h/1h/0h/0/87"),
                "amount": 100_000,
                "prev_hash": TXHASH_b36780,
                "prev_index": 0,
                "script_type": "SPENDWITNESS",
            }
        ],
        "outputs": [
            {
                "address": "2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
                "amount": 40_000,
                "script_type": "PAYTOADDRESS",
            },
            {
                "address": "tb1qe48wz5ysk9mlzhkswcxct9tdjw6ejr2l9e6j8q",
                "amount": 50_000,
                "script_type": "PAYTOADDRESS",
            },
        ],
        "prev_txes": {TXHASH_b36780: protobuf.to_dict(prev_tx, hexlify_bytes=True)},
    }
    tx_file = tmp_path / "tx.json"
    tx_file.write_text(json.dumps(tx))

    result = trezorctl_confirm(client, path, "btc", "sign-tx", str(tx_file))
    assert result.exit_code == 0, result.output
    assert SIGNED_TX in result.output


@pytest.mark.setup_client(uninitialized=True)
def test_device_setup(client: Client, path: str):
    result = trezorctl_confirm(client, path, "device", "setup", "--skip-backup")
    assert result.exit_code == 0, result.output

    result = trezorctl(path, "get-features")
    assert result.exit_code == 0, result.output
    assert "initialized: True" in result.output
    assert "backup_availability: Required" in result.output
