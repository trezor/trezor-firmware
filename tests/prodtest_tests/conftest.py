from __future__ import annotations

import os
import shutil
import socket
import tempfile
import typing as t
from contextlib import contextmanager
from pathlib import Path

import pytest

from trezorlib._internal.emulator import TropicModel
from trezorlib._internal.prodtest_client import ProdtestClient
from trezorlib._internal.prodtest_emulator import get_prodtest_emulator
from trezorlib._internal.prodtest_transport import VcpUdpTransport

from ..emulators import delete_profile
from .tropic_utils import DEFAULT_TROPIC_MODEL_CONFIGFILE, TropicProdtest, TropicSession

# UDP base port for the dedicated Tropic test emulator. Tropic tests run one
#  at a time and tear their emulator down, so a fixed base is safe.
_TROPIC_EMULATOR_UDP_BASE_PORT = 31324


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--prodtest-model",
        action="store",
        default=os.environ.get("TREZOR_MODEL"),
        help="Prodtest model to run tests against (e.g. t3w1, t3t1). "
        "Can also be set via the TREZOR_MODEL environment variable. "
        "If neither is given, the 'latest' emulator build is used.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_command(*names): skip the test unless the device reports all "
        "the given commands in its 'help' listing. Use for model-specific "
        "commands (touch, RGB LED, telemetry, ...).",
    )


@pytest.fixture(scope="session")
def is_emulator(client: ProdtestClient) -> bool:
    """Whether the device under test is an emulator rather than real hardware."""
    return isinstance(client.transport, VcpUdpTransport)


@pytest.fixture(autouse=True)
def skip_if_command_unavailable(
    request: pytest.FixtureRequest, client: ProdtestClient
) -> None:
    """Skip a test whose ``requires_command`` marker names an absent command.

    Model-specific commands are only compiled into some builds. A test declares
    what it needs with ``@pytest.mark.requires_command(Cmd.TOUCH_VERSION)`` and
    is skipped wherever the device doesn't offer it.
    """
    marker = request.node.get_closest_marker("requires_command")
    if marker is None:
        return

    missing = set(marker.args) - client.available_commands
    if missing:
        pytest.skip(f"command(s) not available on this device: {sorted(missing)}")


@pytest.fixture
def tropic_prodtest(
    request: pytest.FixtureRequest,
) -> t.Iterator[TropicProdtest]:
    """Factory for a dedicated prodtest emulator with its own Tropic model.

    Each call starts a fresh ``model_server`` seeded with a config (the
    device-test default, or *tropic_model_configfile* if given), starts a
    prodtest emulator pointed at it, yields a :class:`TropicSession`, and tears
    both down on exit. Following the emulator refactor, the model is a standalone
    process (like ``CoreEmulator`` + the device-test ``tropic_model_port``
    fixture): the emulator only receives its TCP port.

    The model dumps its final state on shutdown (SIGINT), so inspect it *after*
    the ``with`` block::

        def test_pair(tropic_prodtest):
            with tropic_prodtest() as tp:
                tp.client.command_ok(ProdtestCommand(Cmd.TROPIC_PAIR))
            assert tp.state().pairing_key_state(0) == "written"

    This is separate from the shared session emulator used by the other tests:
    inspecting Tropic state requires stopping the model, which a shared,
    session-scoped emulator cannot offer.
    """
    model = request.config.getoption("prodtest_model") or None
    created_dirs: list[str] = []

    @contextmanager
    def _factory(
        *, tropic_model_configfile: str | Path | None = None
    ) -> t.Iterator[TropicSession]:
        config = Path(tropic_model_configfile or DEFAULT_TROPIC_MODEL_CONFIGFILE)
        model_dir = tempfile.mkdtemp(prefix="prodtest_tropic_model_")
        created_dirs.append(model_dir)
        # Let the OS pick a free TCP port for the Tropic model.
        with socket.socket() as s:
            s.bind(("", 0))
            tropic_model_port = s.getsockname()[1]
        tropic_model = TropicModel(
            profile_dir=model_dir,
            configfile=config,
            port=tropic_model_port,
        )
        tropic_model.start()
        try:
            emu_dir = tempfile.mkdtemp(prefix="prodtest_emu_")
            created_dirs.append(emu_dir)
            emu = get_prodtest_emulator(
                model=model,
                profile_dir=emu_dir,
                port=_TROPIC_EMULATOR_UDP_BASE_PORT,
                tropic_model_port=tropic_model.port,
            )
            emu.start()
            client = ProdtestClient(transport=VcpUdpTransport(port=emu.vcp_port))
            session = TropicSession(client, tropic_model)
            try:
                yield session
            finally:
                client.close()
                emu.stop()
        finally:
            # Stop the model after the emulator so it flushes its final state.
            tropic_model.stop()

    try:
        yield _factory
    finally:
        for directory in created_dirs:
            shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture(scope="session")
def client(
    request: pytest.FixtureRequest,
) -> t.Generator[ProdtestClient, None, None]:
    """Yield a client connected to the shared prodtest emulator.

    Session-scoped: a single client (and the single wrapper-started emulator it
    talks to) is shared by every test in the run, so tests that mutate device
    state must restore it. Tropic tests instead use ``tropic_prodtest``, which
    gives each test its own emulator.

    The model is resolved in order:
      1. --prodtest-model CLI option
      2. TREZOR_MODEL environment variable
      3. 'latest' symlink under core/build-xtask/artifacts/latest/prodtest-emu
    """
    model = request.config.getoption("prodtest_model") or None

    # NOTE: the emulator process is started by the `core/prodtest_emu.py` wrapper
    # (or `make test_emu_prodtest`), not here. This object is only used to derive
    # `vcp_port`. Tropic tests run their own emulator (`tropic_prodtest`).
    with tempfile.TemporaryDirectory(
        prefix="prodtest_emu_", delete=delete_profile()
    ) as profile_dir:
        emu = get_prodtest_emulator(model=model, profile_dir=profile_dir)
        with emu:
            client = ProdtestClient(transport=VcpUdpTransport(port=emu.vcp_port))
            # Eagerly resolve the model so any unknown-model error surfaces at startup.
            _ = client.model
            yield client
            client.close()
