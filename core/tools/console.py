#!/usr/bin/env python3
# flake8: noqa: F821, ANN201
# pyright: reportUndefinedVariable=false
# (BlueZ agent methods carry D-Bus type signatures as string annotations, which
#  is also why this file does not use `from __future__ import annotations`.)
"""Console of a Trezor device: the prodtest CLI or the firmware's debug log.

Talks to the device over BLE (the BLE console service), a USB VCP serial port
or the prodtest emulator's UDP. Needs only bleak (which brings dbus-fast on
Linux) and, for --serial, pyserial. No trezorlib.

BLE is the default; without a name or address the tool takes any unit in
range that announces the console service, preferring the one used last. Over
BLE the console is whatever the device routes to it:
- prodtest on a board with [ble_console]: the CLI, both directions; the unit
  advertises as "<MODEL> PT <cpuid>" and accepts pairing by itself;
- firmware built with `--dbg-console ble`: the debug log, output only (input
  is ignored). The first pairing needs "Pair new device" open on the device;
  a bonded host reconnects without it.

By default this is a terminal passthrough, like `screen` on the USB VCP:
keystrokes go to the device as you type and its output comes back verbatim, so
the prodtest CLI's own interactive mode works (press Enter twice to enter it:
echo, line editing, Tab completion and history are then done by the device).
Ctrl-C reaches the device and aborts a running command. Leave with Ctrl-D (or
Ctrl-]).

For the prodtest CLI, --line gives a host-side line prompt instead (with local
history), and a trailing command runs once and exits. Both first put the device
into plain line mode, since a terminal session may have left it interactive.
With --line and commands piped on stdin, one connection runs them all in order:

    printf 'ping\nprodtest-version\n' | console.py --line

For anything more involved, run --serve and drive the device from Python
through trezorlib's ProdtestClient over SerialTransport on the served tty.

Examples:
    console.py                             # the one unit with a console in range
    console.py --ble "T3W1 PT 1A2B3C4D"    # a prodtest unit by name
    console.py --ble "Trezor Safe 7"       # firmware debug log, name prefix
    console.py --ble C0:FF:EE:12:34:56
    console.py --serial /dev/ttyACM0
    console.py --udp                       # the prodtest emulator (UDP 21327)
    console.py --udp 21427                 # emulator started with TREZOR_UDP_PORT=21424
    console.py --line
    console.py ping                        # one command, then exit

Without a name or address the last unit's address is remembered, so the next
start connects to it directly and only scans if it is not in range. Bonds are kept
between sessions so a repeat session skips pairing; if the device dropped its
side of the bond, the host forgets its own and pairs fresh automatically.
--forget-bond forces that from the start.

--serve keeps the connection up (reconnecting whenever it drops, e.g. across
a device reboot) and exposes the console as a pseudo-terminal linked at a
stable path, so any terminal or serial tool can open it like the USB VCP. The
pseudo-terminal exists only while the device is connected: on a drop it is
removed (clients see end-of-file) and it comes back with the reconnect. It
works for a BLE device and for the emulator, where it replaces the socat step:

    console.py --serve                     # device as /tmp/ttyVCP0
    console.py --udp --serve               # emulator as /tmp/ttyVCP0
    screen /tmp/ttyVCP0
    provision_device.py --device /tmp/ttyVCP0
"""

import argparse
import asyncio
import json
import logging
import os
import re
import signal
import sys
import termios
import tty
from pathlib import Path

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

try:
    import readline  # line editing and history for input() in --line mode
except ImportError:  # pragma: no cover
    readline = None

LOG = logging.getLogger("console")

# Trezor wire-protocol service: advertised, used to recognise a Trezor in a scan.
TREZOR_SERVICE_UUID = "8c000001-a59b-4d58-a9ad-073df69fa1b1"
# Console service: prodtest CLI (and debug logs) on firmware that routes it.
CONSOLE_SERVICE_UUID = "8c000010-a59b-4d58-a9ad-073df69fa1b1"
CONSOLE_RX_UUID = "8c000011-a59b-4d58-a9ad-073df69fa1b1"  # host -> device
CONSOLE_TX_UUID = "8c000012-a59b-4d58-a9ad-073df69fa1b1"  # device -> host
PACKET_SIZE = 244

# Prodtest advertises as "<MODEL> PT <cpuid>".
# Trezor's Bluetooth SIG company id, the key of its advertising manufacturer
# data; bit 0x10 of the flags byte (offset 0 after the id) says the BLE console
# service is present.
TREZOR_COMPANY_ID = 0x0F29
ADV_FLAG_CONSOLE = 0x10

SCAN_SECONDS = 3.0
CONNECT_TIMEOUT = 10.0
FORGET_SETTLE_SECONDS = 1.0
RESPONSE_TIMEOUT = 30.0
RECONNECT_DELAY = 2.0

# The emulator's VCP: UDP on TREZOR_UDP_PORT + 3 (21327 with the default
# TREZOR_UDP_PORT), datagrams read into a 64-byte buffer; a PINGPING liveness
# probe is answered with PONGPONG, which is not console data.
EMULATOR_VCP_PORT = 21327
EMULATOR_CHUNK = 64
PING_RESP = b"PONGPONG"
# --serve links the pseudo-terminal here (the name the emulator docs used).
SERVE_PTY = "/tmp/ttyVCP0"

# Prodtest aborts the running command when it sees this byte.
INTERRUPT_BYTE = b"\x03"
# Terminal passthrough leaves on these keys; everything else goes to the device.
EXIT_KEYS = (b"\x04", b"\x1d")  # Ctrl-D, Ctrl-]

FINAL_PREFIXES = ("OK", "ERROR")
# Interactive-mode output: colour escapes and a "> " prompt without a newline.
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PROMPT = "> "

CACHE_DIR = Path.home() / ".cache" / "trezor"
LAST_UNIT_FILE = CACHE_DIR / "console_last.json"
HISTORY_FILE = CACHE_DIR / "console_history"


# ---------------------------------------------------------------------------
# Links: something with async read/write of raw bytes


class BleLink:
    def __init__(
        self,
        client: BleakClient,
        queue: "asyncio.Queue[bytes]",
        agent: object,
        lost: asyncio.Event,
    ) -> None:
        self.client = client
        self.queue = queue
        self.agent = agent  # keeps the agent's bus connection alive
        self.lost = lost  # set when the peripheral disconnects

    async def read(self, timeout: float) -> bytes:
        try:
            return await asyncio.wait_for(self.queue.get(), timeout)
        except asyncio.TimeoutError:
            return b""

    async def write(self, data: bytes) -> None:
        for i in range(0, len(data), PACKET_SIZE):
            # With response: a dropped link shows up as an error, not silence.
            await self.client.write_gatt_char(
                CONSOLE_RX_UUID, data[i : i + PACKET_SIZE], response=True
            )

    async def close(self) -> None:
        try:
            await self.client.disconnect()
        except Exception:
            LOG.debug("disconnect failed", exc_info=True)


class UdpLink:
    """The prodtest emulator's VCP: datagrams to its port, replies come back."""

    class _Proto(asyncio.DatagramProtocol):
        def __init__(self, queue: "asyncio.Queue[bytes]") -> None:
            self.queue = queue

        def datagram_received(self, data: bytes, addr: tuple) -> None:
            if data != PING_RESP:
                self.queue.put_nowait(data)

    def __init__(self) -> None:
        self.queue: "asyncio.Queue[bytes]" = asyncio.Queue()
        self.transport: asyncio.DatagramTransport | None = None
        self.lost = asyncio.Event()  # UDP has no sessions; never set

    @classmethod
    async def open(cls, target: str) -> "UdpLink":
        host, _, port = target.rpartition(":")
        link = cls()
        loop = asyncio.get_running_loop()
        link.transport, _ = await loop.create_datagram_endpoint(
            lambda: cls._Proto(link.queue),
            remote_addr=(host or "127.0.0.1", int(port)),
        )
        return link

    async def read(self, timeout: float) -> bytes:
        try:
            return await asyncio.wait_for(self.queue.get(), timeout)
        except asyncio.TimeoutError:
            return b""

    async def write(self, data: bytes) -> None:
        assert self.transport is not None
        for i in range(0, len(data), EMULATOR_CHUNK):
            self.transport.sendto(data[i : i + EMULATOR_CHUNK])

    async def close(self) -> None:
        if self.transport:
            self.transport.close()


class SerialLink:
    def __init__(self, port: str, baudrate: int = 115200) -> None:
        import serial  # pyserial, only needed for --serial

        self.serial = serial.Serial(port, baudrate, timeout=0.05)
        self.lost = asyncio.Event()  # a tty does not go away; never set

    def _read_blocking(self, timeout: float) -> bytes:
        self.serial.timeout = timeout
        data = self.serial.read(1)
        if data and self.serial.in_waiting:
            data += self.serial.read(self.serial.in_waiting)
        return bytes(data)

    async def read(self, timeout: float) -> bytes:
        return await asyncio.to_thread(self._read_blocking, timeout)

    async def write(self, data: bytes) -> None:
        await asyncio.to_thread(self.serial.write, data)

    async def close(self) -> None:
        self.serial.close()


# ---------------------------------------------------------------------------
# BlueZ: unattended pairing agent and bond removal (Linux only)


class PairingAgent:
    """Confirms numeric-comparison pairing without a desktop dialog.

    Prodtest accepts the pairing on its side automatically; BlueZ asks the
    default agent to confirm on ours. bleak pairs on its own bus connection, so
    this agent has to be registered as the default one.
    """

    PATH = "/com/trezor/console/agent"

    def __init__(self) -> None:
        self.bus = None

    async def register(self) -> None:
        from dbus_fast import BusType, Message
        from dbus_fast.aio import MessageBus
        from dbus_fast.service import ServiceInterface, method

        class Agent(ServiceInterface):
            def __init__(self) -> None:
                super().__init__("org.bluez.Agent1")

            @method()
            def Release(self):  # noqa: N802
                pass

            @method()
            def RequestPinCode(self, device: "o") -> "s":  # noqa: N802
                return "000000"

            @method()
            def DisplayPinCode(self, device: "o", pincode: "s"):  # noqa: N802
                pass

            @method()
            def RequestPasskey(self, device: "o") -> "u":  # noqa: N802
                return 0

            @method()
            def DisplayPasskey(self, device: "o", passkey: "u", entered: "q"):  # noqa: N802
                pass

            @method()
            def RequestConfirmation(self, device: "o", passkey: "u"):  # noqa: N802
                LOG.info("confirming pairing, passkey %06d", passkey)

            @method()
            def RequestAuthorization(self, device: "o"):  # noqa: N802
                pass

            @method()
            def AuthorizeService(self, device: "o", uuid: "s"):  # noqa: N802
                pass

            @method()
            def Cancel(self):  # noqa: N802
                LOG.debug("pairing cancelled")

        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        bus.export(self.PATH, Agent())
        for member, signature, body in (
            ("RegisterAgent", "os", [self.PATH, "KeyboardDisplay"]),
            ("RequestDefaultAgent", "o", [self.PATH]),
        ):
            reply = await bus.call(
                Message(
                    destination="org.bluez",
                    path="/org/bluez",
                    interface="org.bluez.AgentManager1",
                    member=member,
                    signature=signature,
                    body=body,
                )
            )
            if reply is None or reply.error_name:
                raise RuntimeError(f"{member} failed: {reply and reply.error_name}")
        self.bus = bus
        LOG.debug("pairing agent registered")


async def forget_device(device: BLEDevice) -> None:
    """Removes the device and its bond from the local adapter."""
    from dbus_fast import BusType, Message
    from dbus_fast.aio import MessageBus

    path = device.details.get("path") if isinstance(device.details, dict) else None
    if not path:
        return
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        reply = await bus.call(
            Message(
                destination="org.bluez",
                path=path.rsplit("/", 1)[0],
                interface="org.bluez.Adapter1",
                member="RemoveDevice",
                signature="o",
                body=[path],
            )
        )
        if reply is not None and reply.error_name:
            LOG.debug("RemoveDevice: %s", reply.error_name)
        else:
            LOG.info("forgot bond for %s", device.address)
    finally:
        bus.disconnect()
    # BlueZ recreates the device from its next advertisement.
    await asyncio.sleep(FORGET_SETTLE_SECONDS)


# ---------------------------------------------------------------------------
# BLE: finding and connecting


def load_last_unit() -> dict | None:
    try:
        return json.loads(LAST_UNIT_FILE.read_text())
    except (OSError, ValueError):
        return None


def save_last_unit(address: str, name: str | None) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        LAST_UNIT_FILE.write_text(json.dumps({"address": address, "name": name}))
    except OSError:
        pass


def has_console(adv) -> bool:
    """Console service announced in the advertising flags, or already known to
    the host from an earlier connection (BlueZ reports cached GATT UUIDs)."""
    if CONSOLE_SERVICE_UUID in adv.service_uuids:
        return True
    mdata = adv.manufacturer_data.get(TREZOR_COMPANY_ID, b"")
    return len(mdata) >= 1 and bool(mdata[0] & ADV_FLAG_CONSOLE)


async def scan_for_unit(name: str | None) -> BLEDevice:
    """One Trezor with the console service, by name or the only one in range."""
    found = await BleakScanner.discover(timeout=SCAN_SECONDS, return_adv=True)
    trezors = [
        (dev, adv)
        for dev, adv in found.values()
        if TREZOR_SERVICE_UUID in adv.service_uuids and dev.name
    ]
    if name is not None:
        # Exact name, or a unique prefix: the pairing-mode name of regular
        # firmware carries a random suffix, e.g. "Trezor Safe 7 (2P0)".
        matches = [d for d, _ in trezors if d.name == name]
        if not matches:
            matches = [d for d, _ in trezors if (d.name or "").startswith(name)]
    else:
        matches = [d for d, adv in trezors if has_console(adv)]
        if not matches and len(trezors) == 1:
            # An nRF image predating the advertising flag; connecting tells.
            matches = [trezors[0][0]]
    if len(matches) == 1:
        return matches[0]
    seen = ", ".join(f"{d.name} ({d.address})" for d, _ in trezors) or "none"
    if not matches:
        raise RuntimeError(
            f"no unit with a BLE console in range; Trezors seen: {seen}. Prodtest "
            "advertises openly; regular firmware advertises only to bonded hosts, "
            "so for a first connection open 'Pair new device' on the device."
        )
    raise RuntimeError(f"several units in range, give a name or address: {seen}")


async def find_by_address(address: str) -> BLEDevice | None:
    return await BleakScanner.find_device_by_address(address, timeout=SCAN_SECONDS)


async def open_ble(target: str | None, forget_bond: bool) -> BleLink:
    device: BLEDevice | None = None
    remembered = None

    if target is None or target == "auto":
        remembered = load_last_unit()
        if remembered and remembered.get("address"):
            device = await find_by_address(remembered["address"])
            if device is None:
                LOG.info("last unit %s not in range, scanning", remembered["address"])
        if device is None:
            device = await scan_for_unit(None)
    elif ":" in target:
        device = await find_by_address(target)
        if device is None:
            raise RuntimeError(f"{target} is not advertising")
    else:
        device = await scan_for_unit(target)
    assert device is not None

    link = await connect(device, forget_bond)
    name = device.name or (remembered or {}).get("name")
    save_last_unit(device.address, name)
    print(f"connected to {name or device.address}", file=sys.stderr)
    return link


async def connect(device: BLEDevice, forget_bond: bool) -> BleLink:
    if forget_bond and sys.platform == "linux":
        await forget_device(device)
        device = await find_by_address(device.address) or device

    lost = asyncio.Event()

    def on_disconnect(_client: BleakClient) -> None:
        lost.set()

    client = BleakClient(
        device,
        services=[TREZOR_SERVICE_UUID, CONSOLE_SERVICE_UUID],
        timeout=CONNECT_TIMEOUT,
        disconnected_callback=on_disconnect,
    )
    agent: object = None
    try:
        # With a stale host bond BlueZ tries to encrypt during service
        # discovery, the device refuses, and the link drops right here.
        await client.connect()
        if sys.platform == "linux":
            agent = PairingAgent()
            await agent.register()
        try:
            await client.pair()
        except NotImplementedError:
            pass  # macOS pairs on first encrypted access

        if client.services.get_characteristic(CONSOLE_TX_UUID) is None:
            raise RuntimeError(
                f"{device.address} has no BLE console service; it needs prodtest "
                "for a board with [ble_console] or firmware built with "
                "--dbg-console ble"
            )
        queue: "asyncio.Queue[bytes]" = asyncio.Queue()

        def on_notify(_char, data: bytearray) -> None:
            LOG.debug("notification: %d bytes", len(data))
            queue.put_nowait(bytes(data))

        await client.start_notify(CONSOLE_TX_UUID, on_notify)
        LOG.debug("subscribed to console TX notifications")
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        if forget_bond or sys.platform != "linux":
            if forget_bond:
                LOG.error(
                    "pairing failed: prodtest accepts pairing automatically, regular "
                    "firmware only while 'Pair new device' is open on the device"
                )
            raise
        # Most likely a bond mismatch: the device no longer knows us but BlueZ
        # still holds a key for it. Start over with a fresh pairing.
        LOG.warning("connect failed (%s); forgetting bond and pairing fresh", e)
        return await connect(device, forget_bond=True)

    return BleLink(client, queue, agent, lost)


# ---------------------------------------------------------------------------
# Line mode


class LineReader:
    def __init__(self, link) -> None:
        self.link = link
        self.buf = b""

    async def readline(self, timeout: float) -> str | None:
        """Next response line, cleaned of interactive-mode artefacts; None on timeout."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while b"\n" not in self.buf:
            remaining = deadline - loop.time()
            if remaining <= 0:
                return None
            self.buf += await self.link.read(min(remaining, 1.0))
        raw, self.buf = self.buf.split(b"\n", 1)
        line = ANSI_ESCAPE.sub("", raw.decode("utf-8", errors="replace"))
        while line.startswith(PROMPT):
            line = line[len(PROMPT) :]
        return line.strip()


async def leave_interactive_mode(reader: LineReader) -> None:
    """'.' leaves the device's interactive mode and is ignored in line mode."""
    await reader.link.write(b".\r")
    while await reader.readline(0.3) is not None:
        pass


async def run_command(reader: LineReader, line: str, timeout: float) -> bool:
    """Sends one line, prints responses up to the final OK/ERROR."""
    await reader.link.write((line + "\r").encode())
    while True:
        resp = await reader.readline(timeout)
        if resp is None:
            print(f"(no final response within {timeout:g}s)", file=sys.stderr)
            if isinstance(reader.link, UdpLink):
                print(
                    "(emulator: the CLI is on UDP TREZOR_UDP_PORT + 3, "
                    f"{EMULATOR_VCP_PORT} by default)",
                    file=sys.stderr,
                )
            return False
        print(resp)
        if resp.split(" ", 1)[0] in FINAL_PREFIXES:
            return True


def install_interrupt_forwarding(link) -> None:
    """Ctrl-C in line modes aborts the device's command instead of the tool."""
    loop = asyncio.get_running_loop()

    def on_sigint() -> None:
        print("(interrupt sent)", file=sys.stderr)
        loop.create_task(link.write(INTERRUPT_BYTE))

    loop.add_signal_handler(signal.SIGINT, on_sigint)


async def repl(reader: LineReader, timeout: float) -> int:
    interactive = sys.stdin.isatty()
    if interactive and readline is not None:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            readline.read_history_file(HISTORY_FILE)
        except OSError:
            pass
        readline.set_history_length(1000)
        print("type a command, Ctrl-D to exit", file=sys.stderr)
    failures = 0
    try:
        while True:
            try:
                # Piped stdin: no prompt, just run the lines in order.
                line = await asyncio.to_thread(input, "> " if interactive else "")
            except EOFError:
                if interactive:
                    print(file=sys.stderr)
                return 1 if failures else 0
            if line.strip() and not line.lstrip().startswith("#"):
                if not await run_command(reader, line, timeout):
                    failures += 1
    finally:
        if interactive and readline is not None:
            try:
                readline.write_history_file(HISTORY_FILE)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Terminal passthrough


async def terminal(link) -> int:
    if not sys.stdin.isatty():
        print(
            "terminal mode needs a tty; use --line or give a command", file=sys.stderr
        )
        return 2

    fd = sys.stdin.fileno()
    out = sys.stdout.buffer
    loop = asyncio.get_running_loop()
    outgoing: "asyncio.Queue[bytes | None]" = asyncio.Queue()
    done = asyncio.Event()

    def on_stdin() -> None:
        data = os.read(fd, 1024)
        if not data or any(key in data for key in EXIT_KEYS):
            done.set()
            return
        outgoing.put_nowait(data)

    async def pump_keys() -> None:
        while not done.is_set():
            try:
                data = await asyncio.wait_for(outgoing.get(), 0.2)
            except asyncio.TimeoutError:
                continue
            await link.write(data)

    async def pump_device() -> None:
        while not done.is_set():
            try:
                data = await link.read(0.2)
            except Exception as e:
                print(f"\r\n(connection lost: {e})\r\n", file=sys.stderr)
                done.set()
                return
            if data:
                out.write(data)
                out.flush()

    print(
        "terminal mode; Enter twice for the device's interactive mode, Ctrl-D to leave",
        file=sys.stderr,
    )
    saved = termios.tcgetattr(fd)
    tty.setraw(fd)
    loop.add_reader(fd, on_stdin)
    tasks = [asyncio.create_task(pump_keys()), asyncio.create_task(pump_device())]
    try:
        await done.wait()
    finally:
        loop.remove_reader(fd)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        print(file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# --serve: pseudo-terminal with reconnection


class PtyConsole:
    """A pseudo-terminal linked at a stable path, opened like a serial port.

    The tool keeps its own descriptor on the slave side so the master never
    reports EIO when the last client closes. Output while nobody reads is
    buffered by the kernel up to its limit and then dropped, matching the
    console's lossy nature; a client attaching late may see a little of it.
    """

    def __init__(self, link_path: str) -> None:
        self.master, self.slave = os.openpty()
        tty.setraw(self.slave)
        os.set_blocking(self.master, False)
        self.link_path = Path(link_path)
        self.incoming: "asyncio.Queue[bytes]" = asyncio.Queue()
        try:
            if self.link_path.is_symlink() or self.link_path.exists():
                self.link_path.unlink()
            self.link_path.symlink_to(os.ttyname(self.slave))
        except OSError as e:
            raise RuntimeError(f"cannot link pty at {link_path}: {e}") from e
        asyncio.get_running_loop().add_reader(self.master, self._on_readable)

    def _on_readable(self) -> None:
        try:
            data = os.read(self.master, 4096)
        except (BlockingIOError, InterruptedError):
            return
        except OSError:
            return  # no client attached; keep listening
        if data:
            self.incoming.put_nowait(data)

    def send(self, data: bytes) -> None:
        try:
            os.write(self.master, data)
        except (BlockingIOError, OSError):
            pass  # nobody reading fast enough; lossy by design

    def close(self) -> None:
        asyncio.get_running_loop().remove_reader(self.master)
        for fd in (self.master, self.slave):
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            self.link_path.unlink()
        except OSError:
            pass


async def bridge(link, sinks: list) -> None:
    """Relays until the BLE link is lost. Input from any sink goes to the
    device; device output goes to every sink."""

    async def from_sink(sink) -> None:
        while True:
            data = await sink.incoming.get()
            await link.write(data)

    async def to_sinks() -> None:
        while True:
            data = await link.read(0.5)
            if data:
                for sink in sinks:
                    sink.send(data)

    tasks = [asyncio.create_task(from_sink(s)) for s in sinks]
    tasks.append(asyncio.create_task(to_sinks()))
    try:
        await link.lost.wait()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def open_link(args: argparse.Namespace):
    if args.serial:
        return SerialLink(args.serial)
    if args.udp:
        return await UdpLink.open(args.udp)
    return await open_ble(args.ble, args.forget_bond)


async def serve(args: argparse.Namespace) -> int:
    print(f"serving {args.pty}; Ctrl-C to stop", file=sys.stderr)
    while True:
        try:
            link = await open_link(args)
        except Exception as e:
            LOG.warning("connect failed (%s); retrying in %gs", e, RECONNECT_DELAY)
            await asyncio.sleep(RECONNECT_DELAY)
            continue
        # Only a fresh session should pair fresh; reconnects keep the bond.
        args.forget_bond = False

        # The pseudo-terminal mirrors the connection: it appears once the
        # device is reachable and goes away with it, so clients see EOF rather
        # than a stall while the device is off or out of range.
        pty_console = PtyConsole(args.pty)
        print(f"console on tty {args.pty}", file=sys.stderr)
        try:
            await bridge(link, [pty_console])
        finally:
            pty_console.close()
            await link.close()
        print("connection lost, tty removed; reconnecting", file=sys.stderr)
        await asyncio.sleep(RECONNECT_DELAY)


# ---------------------------------------------------------------------------


async def amain(args: argparse.Namespace) -> int:
    if args.serve:
        if args.serial:
            print(
                "--serve is for BLE or UDP; a serial port is a tty already",
                file=sys.stderr,
            )
            return 2
        return await serve(args)
    link = await open_link(args)

    try:
        if args.command or args.line:
            reader = LineReader(link)
            await leave_interactive_mode(reader)
            install_interrupt_forwarding(link)
            if args.command:
                ok = await run_command(reader, " ".join(args.command), args.timeout)
                return 0 if ok else 1
            return await repl(reader, args.timeout)
        return await terminal(link)
    finally:
        await link.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--ble",
        nargs="?",
        const=None,
        metavar="ADDRESS|NAME",
        help="BLE console service of the device; the default, and without a value "
        "any unit with the service (the last one used, if in range)",
    )
    target.add_argument("--serial", metavar="PORT", help="USB VCP serial port")
    target.add_argument(
        "--udp",
        nargs="?",
        const=str(EMULATOR_VCP_PORT),
        metavar="[HOST:]PORT",
        help=f"the prodtest emulator's VCP: TREZOR_UDP_PORT + 3, "
        f"{EMULATOR_VCP_PORT} when omitted",
    )
    parser.add_argument(
        "--forget-bond",
        action="store_true",
        help="forget the host's bond first and pair fresh",
    )
    parser.add_argument(
        "--line",
        action="store_true",
        help="host-side line prompt instead of the terminal passthrough",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="keep the connection up and expose the console as a pseudo-terminal",
    )
    parser.add_argument(
        "--pty",
        default=SERVE_PTY,
        metavar="PATH",
        help=f"with --serve, link the pseudo-terminal at PATH (default {SERVE_PTY})",
    )
    parser.add_argument(
        "--timeout", type=float, default=RESPONSE_TIMEOUT, help="response timeout"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("command", nargs="*", help="run this command and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
    if not args.verbose:
        logging.getLogger("bleak").setLevel(logging.WARNING)

    try:
        return asyncio.run(amain(args))
    except KeyboardInterrupt:
        print(file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
