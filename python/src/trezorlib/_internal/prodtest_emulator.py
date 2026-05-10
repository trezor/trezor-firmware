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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import logging
import socket
import time
import typing as t
from pathlib import Path

from . import emulator
from .emulator import Emulator

LOG = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[4]

# Same as USB_IFACE_BASE_PORT in core/embed/io/usb/usb_config.c
DEFAULT_UDP_BASE_PORT = 21324
# VCP is the 4th interface (offset 3) in the USB configuration
VCP_PORT_OFFSET = 3


class ProdtestEmulator(Emulator):
    """Manages a running prodtest emulator process.

    Extends trezorlib's ``Emulator`` base, overriding ``make_env()`` (adds
    TREZOR_UDP_PORT), ``_wait_until_ready()`` (probes the VCP ``ping`` instead of
    the UDP handshake), and ``start()`` (no debug link). Construct via the
    :func:`get_prodtest_emulator` factory.
    """

    STORAGE_FILENAME = "trezor.flash"

    def __init__(
        self,
        executable: Path,
        profile_dir: str,
        *,
        port: int | None = None,
        headless: bool = True,
        tropic_model_port: int | None = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(
            executable=executable,
            profile_dir=profile_dir,
            headless=headless,
            debug=False,
            auto_interact=False,
            **kwargs,
        )
        if port is not None:
            self.port = port

        # The Tropic model is managed externally (see the ``tropic_prodtest``
        # fixture); we only point the emulator at its port, like CoreEmulator.
        self.tropic_model_port = tropic_model_port

    @property
    def vcp_port(self) -> int:
        """The UDP port for the VCP text interface."""
        return self.port + VCP_PORT_OFFSET

    def make_env(self) -> dict[str, str]:
        env = super().make_env()
        env.update(
            TREZOR_PROFILE_DIR=str(self.profile_dir),
            TREZOR_PROFILE=str(self.profile_dir),
            TREZOR_UDP_PORT=str(self.port),
        )
        if self.headless:
            env["SDL_VIDEODRIVER"] = "dummy"
        if self.tropic_model_port is not None:
            env["TROPIC_MODEL_PORT"] = str(self.tropic_model_port)
        return env

    def _wait_until_ready(self, timeout: float = 30) -> None:
        """
        Wait for the prodtest emulator to accept VCP commands.

        The firmware emulator checks readiness via UdpTransport.is_ready(),
        which sends ``PINGPING`` to the *wire* port and expects ``PONGPONG``.

        The prodtest emulator does not use the wire protocol at all — its
        only interface is the VCP text CLI. So we probe the VCP UDP port
        with a text ``ping`` command and wait for any response (``OK ...``).
        """
        assert self.process is not None, "Emulator not started"
        LOG.info("Waiting for prodtest emulator (VCP port %d)...", self.vcp_port)

        start = time.monotonic()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)

        try:
            while True:
                if self.process.poll() is not None:
                    raise RuntimeError(
                        f"Emulator exited prematurely (code {self.process.returncode})"
                    )

                try:
                    sock.sendto(b"ping\r", ("127.0.0.1", self.vcp_port))
                    data, _ = sock.recvfrom(4096)
                    # Any response means the VCP is alive
                    if data:
                        break
                except socket.timeout:
                    pass

                elapsed = time.monotonic() - start
                if elapsed >= timeout:
                    raise TimeoutError(f"Prodtest emulator not ready after {timeout}s")
                time.sleep(0.1)
        finally:
            sock.close()

        LOG.info("Prodtest emulator ready after %.1fs", time.monotonic() - start)

    def start(self) -> None:
        """
        Start the prodtest emulator.

        Overrides the base Emulator.start() to skip TrezorTestContext creation,
        since prodtest doesn't speak the Trezor wire protocol and has no
        debug link.
        """
        if self.process and self.process.poll() is None:
            return  # already running

        self.process = self._launch_process()
        # Register for atexit cleanup (via base class's _RUNNING_PIDS)

        emulator._RUNNING_PIDS.add(self.process)

        try:
            self._wait_until_ready()
        except TimeoutError:
            LOG.warning("Prodtest emulator did not come up in time")
            self.process.kill()
            raise

        (self.profile_dir / "trezor.pid").write_text(str(self.process.pid) + "\n")
        (self.profile_dir / "trezor.port").write_text(str(self.port) + "\n")

    # stop() is inherited from Emulator


def get_prodtest_emulator(
    model: str | None = None,
    *,
    profile_dir: str,
    port: int | None = None,
    headless: bool = True,
    tropic_model_port: int | None = None,
) -> ProdtestEmulator:
    """Locate a prebuilt binary and return a ready-to-start ProdtestEmulator.

    The binary must already exist (built via ``xtask build prodtest``); otherwise
    ``FileNotFoundError`` is raised. As with the ``Emulator`` base, *profile_dir*
    is caller-owned (e.g. a ``tempfile.TemporaryDirectory``). Pass
    *tropic_model_port* to target an externally-started Tropic ``model_server``.

    Usage::

        with tempfile.TemporaryDirectory() as profile_dir:
            with get_prodtest_emulator("t3w1", profile_dir=profile_dir) as emu:
                emu.start()
                client = ProdtestClient(transport=VcpUdpTransport(port=emu.vcp_port))
    """
    return ProdtestEmulator(
        executable=_find_prodtest_emulator(model),
        profile_dir=profile_dir,
        port=port or DEFAULT_UDP_BASE_PORT,
        headless=headless,
        tropic_model_port=tropic_model_port,
    )


def _find_prodtest_emulator(model: str | None) -> Path:
    """Locate the prodtest emulator binary.

    If *model* is None, use the ``latest`` symlink (``xtask build prodtest
    --latest``), mirroring the convention in ``tests/emulators.py``.
    """
    artifacts = ROOT / "core" / "build-xtask" / "artifacts"

    if model is None:
        path = artifacts / "latest" / "prodtest-emu"
        if path.exists():
            return path
        raise FileNotFoundError(
            "No model specified and no 'latest' prodtest emulator found at "
            f"{path}. Build one with: xtask build prodtest -e -m trezor_model"
        )

    path = artifacts / model.upper() / "prodtest-emu"
    if path.exists():
        return path

    raise FileNotFoundError(
        f"Prodtest emulator binary not found for model {model}. "
        f"Expected path: {path}. "
        f"Build it with: xtask build prodtest -m {model.lower()} -e"
    )
