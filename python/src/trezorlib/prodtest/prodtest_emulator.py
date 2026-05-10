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
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .._internal import emulator
from .._internal.emulator import Emulator

LOG = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
CORE = ROOT / "core"

# Same as USB_IFACE_BASE_PORT in core/embed/io/usb/usb_config.c
DEFAULT_UDP_BASE_PORT = 21324
# VCP is the 4th interface (offset 3) in the USB configuration
VCP_PORT_OFFSET = 3


def _find_prodtest_emulator(model: str | None) -> Path:
    """
    Locate the prodtest emulator binary.

    If *model* is None, falls back to the ``latest`` symlink created by
    ``xtask build prodtest --latest``, mirroring the device-test convention
    in ``tests/emulators.py``.
    """
    artifacts = CORE / "build-xtask" / "artifacts"

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


class ProdtestEmulator(Emulator):
    """
    Manages a running prodtest emulator process.

    Inherits from trezorlib's Emulator base class to reuse:
      - subprocess launch / terminate / kill with timeout
      - atexit PID cleanup (_RUNNING_PIDS)
      - profile directory and PID/port file management
      - __enter__ / __exit__ context manager

    Overrides:
      - make_env(): sets TREZOR_UDP_PORT, TREZOR_PROFILE_DIR, SDL_VIDEODRIVER
      - make_args(): empty (prodtest binary takes no args)
      - _wait_until_ready(): probes the VCP text port with a ``ping`` command
        instead of using UdpTransport's PINGPING/PONGPONG wire handshake
      - start(): skips TrezorTestContext creation (prodtest has no debug link)

    Usage::

        emu = ProdtestEmulator(
            executable=Path("core/build-xtask/artifacts/T3T1/prodtest-emu"),
            profile_dir=tempfile.mkdtemp(),
        )
        emu.start()
        client = ProdtestClient.udp(port=emu.vcp_port)
        client.ping("hello")
        emu.stop()
    """

    STORAGE_FILENAME = "prodtest.flash"

    def __init__(
        self,
        executable: Path,
        profile_dir: str,
        *,
        port: Optional[int] = None,
        headless: bool = True,
        **kwargs: Any,
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

    @property
    def vcp_port(self) -> int:
        """The UDP port for the VCP text interface."""
        return self.port + VCP_PORT_OFFSET

    def make_env(self) -> Dict[str, str]:
        env = super().make_env()
        env.update(
            TREZOR_PROFILE_DIR=str(self.profile_dir),
            TREZOR_PROFILE=str(self.profile_dir),
            TREZOR_UDP_PORT=str(self.port),
        )
        if self.headless:
            env["SDL_VIDEODRIVER"] = "dummy"
        return env

    def make_args(self) -> List[str]:
        # Prodtest binary takes no command-line arguments
        return []

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

    def stop(self) -> None:
        """Stop the emulator, skipping TrezorTestContext teardown."""
        if self.process:
            LOG.info("Terminating prodtest emulator...")
            start_t = time.monotonic()
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
                LOG.info(
                    "Emulator shut down after %.1fs",
                    time.monotonic() - start_t,
                )
            except subprocess.TimeoutExpired:
                LOG.info("Emulator stuck, sending kill signal.")
                self.process.kill()

            emulator._RUNNING_PIDS.discard(self.process)
            emulator._rm_f(self.profile_dir / "trezor.pid")
            emulator._rm_f(self.profile_dir / "trezor.port")
            self.process = None


def get_prodtest_emulator(
    model: str | None = None,
    *,
    port: Optional[int] = None,
    emulator_path: Optional[Path] = None,
    headless: bool = True,
) -> ProdtestEmulator:
    """
    High-level factory that locates (or builds) the binary, creates a
    temp profile dir, and returns a ready-to-start ProdtestEmulator.

    Usage::

        with create_prodtest_emulator("t3t1") as emu:
            client = ProdtestClient.udp(port=emu.vcp_port)
            ...
    """
    if emulator_path is None:
        emulator_path = _find_prodtest_emulator(model)

    profile_dir = tempfile.mkdtemp(prefix="prodtest_emu_")

    return ProdtestEmulator(
        executable=emulator_path,
        profile_dir=profile_dir,
        port=port or DEFAULT_UDP_BASE_PORT,
        headless=headless,
    )
