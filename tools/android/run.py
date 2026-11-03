#!/usr/bin/env python3
"""Run the headless Android emulator on an explicitly selected adb device."""

from __future__ import annotations

import argparse
import selectors
import shlex
import socket
import struct
import subprocess
import threading
import time
from pathlib import Path

APP_PACKAGE = "io.trezor.emulator"
PORT_COUNT = 7


class HostRelay:
    """Carry the host's UDP ports to the device's `udp-relay` over adb TCP.

    Each datagram is framed with its 16-bit big-endian length. As in the
    firmware, replies go to the latest sender on each port.
    """

    def __init__(self, base_port: int) -> None:
        self.selector = selectors.DefaultSelector()
        self.udp: dict[int, socket.socket] = {}
        self.tcp: dict[int, socket.socket] = {}
        self.pending: dict[int, bytes] = {}
        self.peer: dict[int, tuple[str, int]] = {}
        for port in range(base_port, base_port + PORT_COUNT):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", port))
            self.udp[port] = sock
            self.selector.register(sock, selectors.EVENT_READ, ("udp", port))
        threading.Thread(target=self.serve, daemon=True).start()

    def connect(self, port: int) -> socket.socket | None:
        if port not in self.tcp:
            try:
                sock = socket.create_connection(("127.0.0.1", port), timeout=1)
            except OSError:
                return None
            sock.settimeout(None)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.tcp[port] = sock
            self.pending[port] = b""
            self.selector.register(sock, selectors.EVENT_READ, ("tcp", port))
        return self.tcp[port]

    def disconnect(self, port: int) -> None:
        sock = self.tcp.pop(port, None)
        if sock is not None:
            self.selector.unregister(sock)
            sock.close()

    def serve(self) -> None:
        while True:
            for key, _ in self.selector.select():
                kind, port = key.data
                if kind == "udp":
                    data, self.peer[port] = self.udp[port].recvfrom(65535)
                    sock = self.connect(port)
                    try:
                        if sock is not None:
                            sock.sendall(struct.pack(">H", len(data)) + data)
                    except OSError:
                        self.disconnect(port)
                    continue
                try:
                    chunk = self.tcp[port].recv(65537)
                except OSError:
                    chunk = b""
                if not chunk:
                    self.disconnect(port)
                    continue
                buf = self.pending[port] + chunk
                while len(buf) >= 2 and len(buf) >= 2 + (n := buf[0] << 8 | buf[1]):
                    if port in self.peer:
                        self.udp[port].sendto(buf[2 : 2 + n], self.peer[port])
                    buf = buf[2 + n :]
                self.pending[port] = buf


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="adb device serial")
    parser.add_argument("--port", type=int, default=31344, help="UDP base port")
    parser.add_argument(
        "--apk", action="store_true", help="run the APK with the Trezor screen"
    )
    args = parser.parse_args()
    if not 30000 < args.port <= 65536 - PORT_COUNT:
        parser.error(f"--port must be between 30001 and {65536 - PORT_COUNT}")

    adb = ["adb", "-s", args.serial]

    def command(
        *argv: str, capture_output: bool = False
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*adb, *argv], check=True, capture_output=capture_output, text=True
        )

    def shell(script: str) -> str:
        result = command("shell", script, capture_output=True)
        return result.stdout.strip()

    abi = shell("getprop ro.product.cpu.abi")
    if abi not in ("arm64-v8a", "x86_64"):
        parser.error(f"unsupported device ABI: {abi}")
    repo = Path(__file__).resolve().parents[2]
    dist = repo / "core/build/android" / abi / "dist"
    apk = dist.parent / "trezor-emulator.apk"
    for path in (dist / "firmware-emu", dist / "udp-relay", apk):
        if not path.is_file():
            parser.error(f"build {abi} first: {path} is missing")

    remote = f"/data/local/tmp/trezor-android-{args.port}"
    pidfiles = {"udp-relay": f"{remote}/relay.pid"}
    shell(f"mkdir -p {remote}/profile")
    if args.apk:
        command("install", "-r", str(apk), capture_output=True)
        uploads = [dist / "udp-relay"]
    else:
        pidfiles["firmware-emu"] = f"{remote}/firmware.pid"
        uploads = sorted(dist.iterdir())
    command("push", *(str(path) for path in uploads), remote + "/")
    shell(
        f"chmod 700 {remote}/udp-relay"
        + ("" if args.apk else f" {remote}/firmware-emu")
    )

    forwarded: list[int] = []
    relay: subprocess.Popen[str] | None = None
    try:
        # `adb forward` carries only TCP. The device relay converts it to UDP.
        relay = subprocess.Popen(
            [
                *adb,
                "shell",
                f"echo $$ > {pidfiles['udp-relay']} && "
                f"exec {remote}/udp-relay {args.port} {PORT_COUNT}",
            ],
            stdout=subprocess.PIPE,
            text=True,
        )
        assert relay.stdout is not None
        if relay.stdout.readline().strip() != "udp-relay ready":
            raise SystemExit("udp-relay failed to start")
        for port in range(args.port, args.port + PORT_COUNT):
            command("forward", f"tcp:{port}", f"tcp:{port}", capture_output=True)
            forwarded.append(port)
        HostRelay(args.port)
        print(f"export TREZOR_PATH=udp:127.0.0.1:{args.port}", flush=True)

        if args.apk:
            # The app exits its process when the firmware reboots or stops.
            while True:
                command(
                    "shell",
                    f"am start -W -n {APP_PACKAGE}/.TrezorActivity"
                    f" --ei port {args.port}",
                    capture_output=True,
                )
                while shell(f"pidof {APP_PACKAGE} || true"):
                    time.sleep(1)

        environment = {
            "LD_LIBRARY_PATH": remote,
            "SDL_VIDEODRIVER": "dummy",
            "SDL_RENDER_DRIVER": "software",
            "TREZOR_PROFILE_DIR": f"{remote}/profile",
            "TREZOR_PROFILE_NAME": "android",
            "TREZOR_UDP_IP": "0.0.0.0",
            "TREZOR_UDP_PORT": str(args.port),
            "TREZOR_DISABLE_ANIMATION": "1",
        }
        assignments = " ".join(
            shlex.quote(f"{key}={value}") for key, value in environment.items()
        )
        script = (
            f"cd {remote} && echo $$ > {pidfiles['firmware-emu']} && "
            f"exec env {assignments} ./firmware-emu"
        )
        while True:
            result = subprocess.run([*adb, "shell", script], check=False)
            if result.returncode != 3:  # The desktop emulator's reboot exit code.
                return result.returncode
    except KeyboardInterrupt:
        return 130
    finally:
        # Stop only the processes this runner started, including when adb
        # itself was interrupted before it could forward the signal.
        for name, pidfile in pidfiles.items():
            try:
                pid = shell(f"cat {pidfile} 2>/dev/null")
                if pid.isdecimal():
                    executable = shell(f"readlink /proc/{pid}/exe")
                    if executable == f"{remote}/{name}":
                        shell(f"kill {pid}")
            except subprocess.CalledProcessError:
                pass
        if args.apk:
            subprocess.run([*adb, "shell", f"am force-stop {APP_PACKAGE}"], check=False)
        if relay is not None:
            try:
                relay.wait(timeout=5)
            except subprocess.TimeoutExpired:
                relay.kill()
        for port in forwarded:
            subprocess.run(
                [*adb, "forward", "--remove", f"tcp:{port}"],
                check=False,
                capture_output=True,
            )


if __name__ == "__main__":
    raise SystemExit(main())
