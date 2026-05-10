from __future__ import annotations

import os
import typing as t

import pytest

from trezorlib.prodtest.prodtest_client import ProdtestClient
from trezorlib.prodtest.prodtest_emulator import get_prodtest_emulator
from trezorlib.prodtest.prodtest_transport import VcpUdpTransport


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--prodtest-model",
        action="store",
        default=os.environ.get("TREZOR_MODEL"),
        help="Prodtest model to run tests against (e.g. t3w1, t3t1). "
        "Can also be set via the TREZOR_MODEL environment variable. "
        "If omitted, the 'latest' emulator build is used.",
    )


@pytest.fixture(scope="session")
def prodtest_client(
    request: pytest.FixtureRequest,
) -> t.Generator[ProdtestClient, None, None]:
    """Start a prodtest emulator and yield a connected client.

    The model is resolved in order:
      1. --prodtest-model CLI option
      2. TREZOR_MODEL environment variable
      3. 'latest' symlink under core/build-xtask/artifacts/latest/prodtest-emu
    """
    model = request.config.getoption("prodtest_model") or None

    emu = get_prodtest_emulator(model=model)
    with emu:
        client = ProdtestClient(transport=VcpUdpTransport(port=emu.vcp_port))
        # Eagerly resolve the model so any unknown-model error surfaces at startup.
        _ = client.model
        yield client
        client.close()
