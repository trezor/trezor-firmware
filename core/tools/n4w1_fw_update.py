#!/usr/bin/env python3
"""
Update the firmware of an N4W1 NFC card through prodtest.

prodtest is switched into NFC transparent mode (`nfc-backup-transparent-mode`)
and the firmware update APDUs are tunnelled to the card using the
`transceive <hex>` command.

    1. START             - card reports which bank (0/1) will be written
    2. SET FINGERPRINT   - fingerprint + proof of the firmware for that bank
    3. VERIFY SIGNATURE  - every signature from the package, sent in blocks
    4. WRITE CHUNK       - firmware payload, chunk by chunk, each with its hash
    5. FINISH            - card verifies the written image
    6. card reset
    7. CONFIRM           - card confirms the new firmware after the trial run
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import click
import serial

# ---------------------------------------------------------------------------
# Firmware update APDU definitions 
# ---------------------------------------------------------------------------

CLA_FW_UPDATE = 0x80

INS_FW_UPDATE_START = 0x10
INS_FW_UPDATE_SET_FINGERPRINT = 0x11
INS_FW_UPDATE_VERIFY_SIGNATURE = 0x12
INS_FW_UPDATE_WRITE_CHUNK = 0x13
INS_FW_UPDATE_FINISH = 0x14
INS_FW_UPDATE_ABORT = 0x15
INS_FW_UPDATE_CONFIRM = 0x16

SW_OK = 0x9000

# Size of the header (type, id, offset LE16) prepended to every signature block
SIGNATURE_BLOCK_HEADER_SIZE = 4

# Written firmware chunks have to be aligned to this size
CHUNK_ALIGNMENT = 32

# Size of the line buffer in prodtest transparent mode (prodtest_nfc_backup.c)
TM_LINE_BUFFER_SIZE = 1024

SUPPORTED_PACKAGE_VERSION = 1

# Aborts the running prodtest command (ASCII ETX)
CTRL_C = b"\x03"


class FwUpdateError(Exception):
    pass


# ---------------------------------------------------------------------------
# Firmware package (signed-app.json)
# ---------------------------------------------------------------------------


@dataclass
class FirmwareImage:
    """Firmware image for one flash bank."""

    payload: bytes
    fingerprint: bytes
    proof: bytes
    chunk_hashes: list[bytes]


@dataclass
class Signature:
    type: int
    id: int
    data: bytes


@dataclass
class FirmwarePackage:
    """Parsed content of the signed-app.json file."""

    version: int
    chunk_size: int
    firmware: list[FirmwareImage]  # indexed by bank number
    signatures: list[Signature]

    @classmethod
    def load(cls, path: Path) -> FirmwarePackage:
        content = json.loads(path.read_text())

        version = content["version"]
        if version != SUPPORTED_PACKAGE_VERSION:
            raise FwUpdateError(f"Unsupported package version {version}")

        chunk_size = content["chunkSize"]

        firmware = []
        for bank, fw in enumerate(content["firmware"]):
            image = FirmwareImage(
                payload=bytes.fromhex(fw["payload"]),
                fingerprint=bytes.fromhex(fw["fingerprint"]),
                proof=bytes.fromhex(fw["proof"]),
                chunk_hashes=[bytes.fromhex(h) for h in fw["chunkHashes"]],
            )

            if len(image.payload) != fw["size"]:
                raise FwUpdateError(f"Bank {bank}: payload size mismatch")

            expected_chunks = -(-len(image.payload) // chunk_size)
            if len(image.chunk_hashes) != expected_chunks:
                raise FwUpdateError(f"Bank {bank}: chunk hash count mismatch")

            firmware.append(image)

        signatures = [
            Signature(
                type=sig["type"],
                id=sig["id"],
                data=bytes.fromhex(sig["signature"]),
            )
            for sig in content["signatures"]
        ]

        return cls(version, chunk_size, firmware, signatures)


# ---------------------------------------------------------------------------
# APDU encoding 
# ---------------------------------------------------------------------------


def build_apdu(
    cla: int, ins: int, p1: int = 0, p2: int = 0, data: bytes = b"", le: int = 0
) -> bytes:
    """Encode a command APDU using short or extended Lc/Le as needed."""
    apdu = bytes([cla, ins, p1, p2])
    lc = len(data)

    if lc > 0:
        if lc <= 0xFF:
            apdu += bytes([lc])
        else:
            apdu += b"\x00" + lc.to_bytes(2, "big")
        apdu += data

    if le > 0:
        if le <= 0x100:
            apdu += bytes([le & 0xFF])
        elif lc == 0:
            apdu += b"\x00" + le.to_bytes(2, "big")
        else:
            apdu += le.to_bytes(2, "big")

    return apdu


# ---------------------------------------------------------------------------
# prodtest NFC transparent mode
# ---------------------------------------------------------------------------


class TransparentMode:
    """Wrapper for the prodtest `nfc-backup-transparent-mode` command set."""

    def __init__(self, ser: serial.Serial) -> None:
        self.ser = ser

    def enter(self) -> None:
        """Enter transparent mode, leaving it first if it is already running."""
        self.exit()
        # Exit a possibly running interactive mode
        self.ser.write(b".\r\n")
        time.sleep(0.1)
        self.ser.reset_input_buffer()
        self._send_line("nfc-backup-transparent-mode")
        self._wait_for_line("Entering transparent mode", timeout=2)

    def exit(self) -> None:
        """Leave transparent mode (no-op if prodtest is not in it).

        Ctrl+C aborts the running prodtest command; leaving transparent mode
        also turns the NFC off.
        """
        self.ser.write(CTRL_C)
        time.sleep(0.1)
        self.ser.reset_input_buffer()

    def on(self) -> None:
        self._expect_ok("on")

    def off(self) -> None:
        self._expect_ok("off")

    def reset(self) -> None:
        """Power-cycle the NFC field and wait for the card to reconnect."""
        self._expect_ok("reset")
        self.wait_for_card()

    def wait_for_card(self) -> None:
        click.echo("Waiting for NFC card...")
        self._wait_for_line("NFC card connected.")

    def transceive(self, apdu: bytes) -> tuple[bytes, int]:
        """Send an APDU to the card, return (response data, status word)."""
        resp = self._command(f"transceive {apdu.hex()}")

        try:
            raw = bytes.fromhex(resp)
        except ValueError:
            raise FwUpdateError(f"Transceive failed: {resp}") from None

        if len(raw) < 2:
            raise FwUpdateError(f"Response too short: {resp}")

        return raw[:-2], int.from_bytes(raw[-2:], "big")

    def _send_line(self, line: str) -> None:
        if len(line) >= TM_LINE_BUFFER_SIZE:
            raise FwUpdateError(f"Command too long ({len(line)} chars)")
        click.echo(f"> {line}")
        self.ser.write((line + "\r\n").encode())

    def _read_line(self) -> str:
        raw = self.ser.readline()
        if not raw:
            raise FwUpdateError("Timeout waiting for prodtest response")
        return raw.decode(errors="ignore").strip()

    def _command(self, line: str) -> str:
        """Send a command and return its response, skipping trace lines."""
        self.ser.reset_input_buffer()
        self._send_line(line)

        while True:
            resp = self._read_line()
            if not resp:
                continue  # empty line
            if resp.startswith("#"):
                # Asynchronous trace line (e.g. card connected/removed)
                click.echo(resp)
                continue
            click.echo(f"< {resp}")
            return resp

    def _expect_ok(self, line: str) -> None:
        resp = self._command(line)
        if resp != "OK":
            raise FwUpdateError(f"Command '{line}' failed: {resp}")

    def _wait_for_line(self, expected: str, timeout: float | None = None) -> None:
        """Read lines until one contains `expected` (forever if no timeout)."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while deadline is None or time.monotonic() < deadline:
            line = self.ser.readline().decode(errors="ignore").strip()
            if line:
                click.echo(line)
            if expected in line:
                return
        raise FwUpdateError(f"Timeout waiting for '{expected}'")


# ---------------------------------------------------------------------------
# Firmware update protocol 
# ---------------------------------------------------------------------------


class CardFwUpdater:
    def __init__(self, tm: TransparentMode) -> None:
        self.tm = tm

    def _command(
        self, name: str, ins: int, data: bytes = b"", le: int = 0
    ) -> bytes:
        apdu = build_apdu(CLA_FW_UPDATE, ins, data=data, le=le)
        resp_data, sw = self.tm.transceive(apdu)
        if sw != SW_OK:
            raise FwUpdateError(f"{name} failed with status 0x{sw:04X}")
        return resp_data

    def start(self) -> int:
        """Start the update and return the bank number to be written."""
        resp = self._command("Start", INS_FW_UPDATE_START, le=1)
        if len(resp) != 1 or resp[0] not in (0, 1):
            raise FwUpdateError(f"Unexpected bank number: {resp.hex()}")
        return resp[0]

    def set_fingerprint(self, fingerprint: bytes, proof: bytes) -> None:
        self._command(
            "Set fingerprint", INS_FW_UPDATE_SET_FINGERPRINT, fingerprint + proof
        )

    def verify_signature(self, sig: Signature, block_size: int) -> None:
        """Upload one signature split into blocks of `block_size` bytes."""
        for offset in range(0, len(sig.data), block_size):
            header = bytes([sig.type, sig.id]) + offset.to_bytes(2, "little")
            block = sig.data[offset : offset + block_size]
            self._command(
                "Verify signature", INS_FW_UPDATE_VERIFY_SIGNATURE, header + block
            )

    def write_chunk(self, chunk: bytes, chunk_hash: bytes) -> None:
        # Pad the (last) chunk to a multiple of CHUNK_ALIGNMENT bytes
        padding = -len(chunk) % CHUNK_ALIGNMENT
        chunk += bytes(padding)
        self._command("Write chunk", INS_FW_UPDATE_WRITE_CHUNK, chunk_hash + chunk)

    def finish(self) -> None:
        self._command("Finish", INS_FW_UPDATE_FINISH)

    def abort(self) -> None:
        self._command("Abort", INS_FW_UPDATE_ABORT)

    def confirm(self) -> None:
        self._command("Confirm", INS_FW_UPDATE_CONFIRM)


def upload_firmware(updater: CardFwUpdater, package: FirmwarePackage) -> None:
    """Steps 1-5 of the update procedure."""
    bank = updater.start()
    click.echo(f"Firmware will be uploaded to bank {bank}")
    fw = package.firmware[bank]

    click.echo("Verifying signatures...")
    updater.set_fingerprint(fw.fingerprint, fw.proof)

    # The signature block (incl. its header) has the same size as a data chunk
    block_size = package.chunk_size - SIGNATURE_BLOCK_HEADER_SIZE
    for sig in package.signatures:
        updater.verify_signature(sig, block_size)

    click.echo(f"Uploading firmware to bank {bank}...")
    chunk_size = package.chunk_size
    total_chunks = len(fw.chunk_hashes)
    for idx, chunk_hash in enumerate(fw.chunk_hashes):
        chunk = fw.payload[idx * chunk_size : (idx + 1) * chunk_size]
        updater.write_chunk(chunk, chunk_hash)
        click.echo(f"Uploaded chunk {idx + 1}/{total_chunks}")

    click.echo("Finishing update...")
    updater.finish()


def update_card(tm: TransparentMode, package: FirmwarePackage) -> None:
    """Run the whole update procedure in transparent mode."""
    updater = CardFwUpdater(tm)

    tm.on()
    tm.wait_for_card()

    tic = time.time()
    try:
        upload_firmware(updater, package)
    except FwUpdateError:
        click.echo("Update failed, aborting...", err=True)
        try:
            updater.abort()
        except FwUpdateError as e:
            click.echo(f"Abort failed: {e}", err=True)
        raise
    click.echo(f"Upload took {time.time() - tic:.2f} seconds")

    # Reboot the card into the new firmware and confirm it
    tm.reset()
    click.echo("Confirming update...")
    updater.confirm()
    click.echo("Firmware update completed successfully.")


def run(port: str, package_path: Path) -> None:
    package = FirmwarePackage.load(package_path)
    click.echo(
        f"Loaded {package_path} (version {package.version}, "
        f"{len(package.firmware)} banks, {len(package.signatures)} signatures, "
        f"chunk size {package.chunk_size})"
    )

    with serial.Serial(port, timeout=2) as ser:
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        tm = TransparentMode(ser)

        tm.enter()
        try:
            update_card(tm, package)
        finally:
            # Always return prodtest to the normal CLI (also turns NFC off)
            tm.exit()


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("port", metavar="<serial-port>")
@click.argument(
    "package",
    metavar="<signed-app.json>",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def main(port: str, package: Path) -> None:
    """
    <serial-port> e.g. /dev/ttyUSB0 or COM3

    <signed-app.json> signed firmware package containing both banks
    """
    try:
        run(port, package)
    except FwUpdateError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except serial.SerialException as e:
        click.echo(f"Serial error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("Interrupted by user.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
