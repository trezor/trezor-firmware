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

"""Emulation of the K1N1 card at the APDU level.

Implements the card side of the K1N1 card API v02: application selection, PSK
exchange, Noise XXpsk3 handshake, secure messaging and the system and API
commands. Firmware update, provisioning and the NDEF file system are not
emulated.
"""

from __future__ import annotations

import functools
import logging
import os
import typing as t
from dataclasses import dataclass
from enum import IntEnum

from noise.connection import Keypair, NoiseConnection
from noise.exceptions import NoiseHandshakeError, NoiseInvalidMessage

from trezorlib.debuglink import DebugLink

LOG = logging.getLogger(__name__)

AID_K1N1 = bytes.fromhex("a0000009590001")

NOISE_PROTOCOL = b"Noise_XXpsk3_25519_AESGCM_SHA256"
PSK_SHARE_LEN = 16
PIN_FIELD_LEN = 32
MAX_PIN_ATTEMPTS = 10
SEED_LEN = 256
SEED_METADATA_LEN = 256

OS_VERSION = bytes((0, 2, 0))
# measured on a real card, depends on how well the card is powered
CPU_FREQUENCY_KHZ = 34_451
WELCOME_MESSAGE = b"K1N1\x00"
# Placeholder for the 403-byte DER certificate sent in Noise message 2.
DUMMY_CERTIFICATE = b"\x30\x82\x01\x8f" + bytes(399)
# Answer to a PSK frame that fails validation.
PSK_REJECTED = b"\x69\xf0"


class SW(IntEnum):
    """Status words (card API, section 4.2)."""

    OK = 0x9000
    SYSTEM_INTERNAL = 0xF001
    COMMAND_INVALID = 0xF101
    COMMAND_INVALID_FORMAT = 0xF102
    COMMAND_INVALID_PARAMETERS = 0xF103
    COMMAND_INTERNAL_ERROR = 0xF104
    API_HANDSHAKE_REQUIRED = 0xF301
    API_PERMISSION_DENIED = 0xF302
    API_PSK_NOT_AVAILABLE = 0xF303
    API_INVALID_DATA_FORMAT = 0xF304
    API_INVALID_PIN_FORMAT = 0xF305


class ApduFormatError(ValueError):
    pass


class CardError(Exception):
    """Raised by command handlers to answer with a status word."""

    def __init__(self, sw: SW) -> None:
        super().__init__(sw)
        self.sw = sw


@dataclass(frozen=True)
class CommandApdu:
    """ISO/IEC 7816-4 command APDU, short or extended length encoding."""

    cla: int
    ins: int
    p1: int = 0
    p2: int = 0
    data: bytes = b""
    # Maximum response length; `None` if Le is absent. An encoded zero is
    # stored as its meaning: 256 (short) or 65536 (extended).
    le: int | None = None

    @classmethod
    def parse(cls, raw: bytes) -> CommandApdu:
        if len(raw) < 4:
            raise ApduFormatError("APDU shorter than its header")
        cla, ins, p1, p2 = raw[:4]
        body = raw[4:]
        data = b""
        le = None
        if not body:
            # case 1: no data, no Le
            pass
        elif len(body) == 1:
            # case 2S: short Le
            le = body[0] or 256
        elif body[0] != 0:
            # case 3S/4S: short Lc, data, optional short Le
            lc = body[0]
            data = body[1 : 1 + lc]
            if len(body) == 1 + lc:
                pass
            elif len(body) == 2 + lc:
                le = body[-1] or 256
            else:
                raise ApduFormatError("Lc inconsistent with APDU length")
        elif len(body) == 3:
            # case 2E: extended Le
            le = int.from_bytes(body[1:3], "big") or 65536
        else:
            # case 3E/4E: extended Lc, data, optional extended Le
            lc = int.from_bytes(body[1:3], "big")
            data = body[3 : 3 + lc]
            if lc == 0:
                raise ApduFormatError("Extended Lc of zero")
            if len(body) == 3 + lc:
                pass
            elif len(body) == 5 + lc:
                le = int.from_bytes(body[-2:], "big") or 65536
            else:
                raise ApduFormatError("Lc inconsistent with APDU length")
        return cls(cla, ins, p1, p2, data, le)

    @property
    def cla_ins(self) -> int:
        """CLA and INS as a single 16-bit value, e.g. 0x800D for WRITE SEED."""
        return self.cla << 8 | self.ins

    def encode(self) -> bytes:
        """Encode like the firmware does: short form if both lengths fit."""
        header = bytes((self.cla, self.ins, self.p1, self.p2))
        lc = le = b""
        if len(self.data) <= 255 and (self.le or 0) <= 256:
            if self.data:
                lc = bytes((len(self.data),))
            if self.le is not None:
                le = bytes((self.le % 256,))
        else:
            if self.data:
                lc = b"\x00" + len(self.data).to_bytes(2, "big")
            if self.le is not None:
                # extended Le has its own 0x00 prefix only without Lc
                le = (b"" if self.data else b"\x00") + (self.le % 65536).to_bytes(
                    2, "big"
                )
        return header + lc + self.data + le

    def __str__(self) -> str:
        s = f"{self.cla:02x} {self.ins:02x} {self.p1:02x} {self.p2:02x}"
        if self.data:
            s += f" [{len(self.data)}] {self.data.hex()}"
        if self.le is not None:
            s += f" le={self.le}"
        return s


@dataclass(frozen=True)
class PskShare:
    """The reader's share of the custom PSK exchange (card API, chapter 3).

    Sent to the card in place of an APDU; the card answers with its own share.
    """

    share: bytes


Frame = bytes | PskShare


def decode_pin(field: bytes) -> str:
    """Decode the 32-byte PIN field (card API, section 7.1)."""
    if len(field) != PIN_FIELD_LEN:
        raise CardError(SW.API_INVALID_PIN_FORMAT)
    end = field.find(0xFF)
    if end < 0:
        end = len(field)
    digits, padding = field[:end], field[end:]
    if not all(0x30 <= b <= 0x39 for b in digits) or padding.strip(b"\xff"):
        raise CardError(SW.API_INVALID_PIN_FORMAT)
    return digits.decode()


class K1N1Tag:
    """Emulated card: persistent content of the secure storage.

    `tap()` returns the generator that represents one activation.
    """

    def __init__(
        self,
        uid: bytes | None = None,
        static_private_key: bytes | None = None,
        pin: str = "",
        seed: bytes | None = None,
    ) -> None:
        # anticollision UID, also returned by GET UID
        self.uid = uid or os.urandom(7)
        # Noise static key, certified by the (dummy) card certificate
        self.static_private_key = static_private_key or os.urandom(32)
        # secure storage (card API, section 7.1)
        self.pin = pin
        self.pin_counter = MAX_PIN_ATTEMPTS
        self.success_log = bytes(32)
        self.failure_logs: list[bytes] = []
        self.seed = seed
        self.seed_metadata = bytes(SEED_METADATA_LEN)

        self._activation: t.Generator[bytes, Frame, None] | None = None

    def wipe(self) -> None:
        self.pin = ""
        self.pin_counter = MAX_PIN_ATTEMPTS
        self.success_log = bytes(32)
        self.failure_logs = []
        self.seed = None
        self.seed_metadata = bytes(SEED_METADATA_LEN)

    def to_dict(self) -> dict[str, t.Any]:
        return {
            "uid": self.uid.hex(),
            "static_private_key": self.static_private_key.hex(),
            "pin": self.pin,
            "pin_counter": self.pin_counter,
            "success_log": self.success_log.hex(),
            "failure_logs": [log.hex() for log in self.failure_logs],
            "seed": self.seed.hex() if self.seed is not None else None,
            "seed_metadata": self.seed_metadata.hex(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, t.Any]) -> K1N1Tag:
        card = cls(
            uid=bytes.fromhex(d["uid"]),
            static_private_key=bytes.fromhex(d["static_private_key"]),
            pin=d["pin"],
            seed=bytes.fromhex(d["seed"]) if d["seed"] is not None else None,
        )
        card.pin_counter = d["pin_counter"]
        card.success_log = bytes.fromhex(d["success_log"])
        card.failure_logs = [bytes.fromhex(log) for log in d["failure_logs"]]
        card.seed_metadata = bytes.fromhex(d["seed_metadata"])
        return card

    def tap(self) -> t.Generator[bytes, Frame, None]:
        """Power the card on.

        The first `next()` yields the UID. Then every `send()` of a frame
        (command APDU or `PskShare`) returns the card's response. Closing the
        generator removes the card from the field, which ends the session.
        """
        session = _Session(self)
        frame = yield self.uid
        while True:
            frame = yield session.process(frame)

    def __enter__(self) -> t.Generator[bytes, Frame, None]:
        self._activation = self.tap()
        return self._activation

    def __exit__(self, exc_type: t.Any, exc_value: t.Any, traceback: t.Any) -> None:
        if self._activation is not None:
            self._activation.close()
            self._activation = None


Handler = t.Callable[["_Session", CommandApdu], bytes]

# command handlers by CLA and INS, registered by `@command`
_COMMANDS: dict[int, Handler] = {}


def check_data_len(apdu: CommandApdu, length: int) -> None:
    if len(apdu.data) != length:
        raise CardError(SW.API_INVALID_DATA_FORMAT)


def command(
    cla_ins: int,
    *,
    handshake: bool = False,
    auth: bool = False,
    data_len: int | None = None,
) -> t.Callable[[Handler], Handler]:
    """Register a command handler, checking its preconditions in this order:

    - the handshake is completed, if `handshake` or `auth`,
    - the session is authenticated, if `auth`,
    - the command data has `data_len` bytes, if given.

    The access levels are defined in the card API, section 4.6. P1 and P2 are
    ignored, like the real card does, unless the handler checks them.
    """

    def decorator(func: Handler) -> Handler:
        @functools.wraps(func)
        def wrapper(self: _Session, apdu: CommandApdu) -> bytes:
            if (handshake or auth) and not self.secure:
                raise CardError(SW.API_HANDSHAKE_REQUIRED)
            if auth and not self.authenticated:
                raise CardError(SW.API_PERMISSION_DENIED)
            if data_len is not None:
                check_data_len(apdu, data_len)
            return func(self, apdu)

        assert cla_ins not in _COMMANDS
        _COMMANDS[cla_ins] = wrapper
        return wrapper

    return decorator


class _Session:
    """State bound to a single activation (card API, section 4.6)."""

    def __init__(self, card: K1N1Tag) -> None:
        self.card = card
        self.aid_selected = False
        self.psk: bytes | None = None
        self.noise: NoiseConnection | None = None
        self.handshake_step1_done = False
        self.secure = False
        self.reader_static_key: bytes | None = None
        self.authenticated = False

    def process(self, frame: Frame) -> bytes:
        if isinstance(frame, PskShare):
            return self.psk_exchange(frame.share)
        if not self.secure:
            if not frame:
                # empty I-block, used as a presence check
                return SW.OK.to_bytes(2, "big")
            data, sw = self.execute(frame)
            return data + sw.to_bytes(2, "big")

        # secure messaging (card API, section 4.5)
        assert self.noise is not None
        try:
            plaintext = bytes(self.noise.decrypt(frame))
        except NoiseInvalidMessage:
            LOG.debug("> (failed to decrypt) %s", frame.hex())
            LOG.debug("< %04x %s", SW.COMMAND_INVALID, SW.COMMAND_INVALID.name)
            return SW.COMMAND_INVALID.to_bytes(2, "big")
        data, sw = self.execute(plaintext)
        return bytes(self.noise.encrypt(data)) + sw.to_bytes(2, "big")

    def execute(self, raw: bytes) -> tuple[bytes, SW]:
        try:
            apdu = CommandApdu.parse(raw)
        except ApduFormatError as e:
            LOG.debug("> (%s) %s", e, raw.hex())
            LOG.debug(
                "< %04x %s", SW.COMMAND_INVALID_FORMAT, SW.COMMAND_INVALID_FORMAT.name
            )
            return b"", SW.COMMAND_INVALID_FORMAT

        LOG.debug("> %s", apdu)
        # handshake step 2 has to follow step 1 immediately
        if apdu.cla_ins != 0x8001:
            self.handshake_step1_done = False

        handler = _COMMANDS.get(apdu.cla_ins)
        try:
            if handler is None:
                raise CardError(SW.COMMAND_INVALID)
            data, sw = handler(self, apdu), SW.OK
        except CardError as e:
            data, sw = b"", e.sw
        LOG.debug("< %s%04x %s", f"[{len(data)}] " if data else "", sw, sw.name)
        return data, sw

    # PSK exchange (card API, chapter 3)

    def psk_exchange(self, reader_share: bytes) -> bytes:
        LOG.debug("> PSK share %s", reader_share.hex())
        if self.psk is not None:
            raise NotImplementedError("Only one PSK exchange per tap is emulated")
        if not self.aid_selected or len(reader_share) != PSK_SHARE_LEN:
            LOG.debug("< PSK rejected")
            return PSK_REJECTED
        card_share = os.urandom(PSK_SHARE_LEN)
        self.psk = reader_share + card_share
        LOG.debug("< PSK share %s", card_share.hex())
        return card_share

    # ISO commands (card API, sections 2.5 and 4.3)

    @command(0x00A4)
    def select(self, apdu: CommandApdu) -> bytes:
        if (apdu.p1, apdu.p2) != (0x04, 0x00) or apdu.data != AID_K1N1:
            raise NotImplementedError(
                f"Only selecting the K1N1 AID is emulated: {apdu}"
            )
        self.aid_selected = True
        return b""

    # system commands (card API, chapter 5)

    @command(0x2001)
    def get_os_version(self, apdu: CommandApdu) -> bytes:
        return OS_VERSION

    @command(0x2002)
    def get_uid(self, apdu: CommandApdu) -> bytes:
        if len(self.card.uid) != 7:
            raise CardError(SW.SYSTEM_INTERNAL)
        return self.card.uid

    @command(0x2003)
    def measure_cpu_frequency(self, apdu: CommandApdu) -> bytes:
        return CPU_FREQUENCY_KHZ.to_bytes(4, "big")

    @command(0x2004)
    def harden_memory(self, apdu: CommandApdu) -> bytes:
        return b""

    @command(0x2005)
    def integrity_check(self, apdu: CommandApdu) -> bytes:
        return bytes(12)  # no ECC events

    # API commands (card API, chapter 7)

    @command(0x8001)
    def handshake(self, apdu: CommandApdu) -> bytes:
        if (apdu.p1, apdu.p2) == (0x00, 0x00):
            check_data_len(apdu, 48)
            if self.psk is None:
                raise CardError(SW.API_PSK_NOT_AVAILABLE)
            noise = NoiseConnection.from_name(NOISE_PROTOCOL)
            noise.set_as_responder()
            noise.set_keypair_from_private_bytes(
                Keypair.STATIC, self.card.static_private_key
            )
            noise.set_psks(self.psk)
            noise.start_handshake()
            try:
                noise.read_message(apdu.data)
                message2 = bytes(noise.write_message(DUMMY_CERTIFICATE))
            except (NoiseInvalidMessage, NoiseHandshakeError) as e:
                raise CardError(SW.COMMAND_INTERNAL_ERROR) from e
            self.noise = noise
            self.handshake_step1_done = True
            return message2

        if (apdu.p1, apdu.p2) == (0x01, 0x00):
            check_data_len(apdu, 64)
            if not self.handshake_step1_done or self.noise is None:
                raise CardError(SW.COMMAND_INTERNAL_ERROR)
            self.handshake_step1_done = False
            # `NoiseConnection` drops the handshake state once the handshake is
            # finished, keep it to read the reader's static key.
            assert self.noise.noise_protocol is not None
            handshake_state = self.noise.noise_protocol.handshake_state
            try:
                self.noise.read_message(apdu.data)
            except (NoiseInvalidMessage, NoiseHandshakeError) as e:
                raise CardError(SW.COMMAND_INTERNAL_ERROR) from e
            self.reader_static_key = bytes(handshake_state.rs.public_bytes)
            self.secure = True
            return bytes(self.noise.encrypt(WELCOME_MESSAGE))

        raise CardError(SW.COMMAND_INVALID_PARAMETERS)

    @command(0x8003, data_len=0)
    def pin_unlocked(self, apdu: CommandApdu) -> bytes:
        if self.card.pin:
            raise CardError(SW.API_PERMISSION_DENIED)
        return b""

    @command(0x8004, handshake=True)
    def authenticate(self, apdu: CommandApdu) -> bytes:
        pin = decode_pin(apdu.data)
        assert self.reader_static_key is not None
        card = self.card
        # the attempt is counted before the PIN is checked
        card.pin_counter -= 1
        card.failure_logs.append(self.reader_static_key)
        if pin != card.pin:
            if card.pin_counter == 0:
                card.wipe()
            raise CardError(SW.API_PERMISSION_DENIED)
        card.pin_counter = MAX_PIN_ATTEMPTS
        card.failure_logs = []
        card.success_log = self.reader_static_key
        self.authenticated = True
        return b""

    @command(0x8005, auth=True)
    def set_pin(self, apdu: CommandApdu) -> bytes:
        self.card.pin = decode_pin(apdu.data)
        return b""

    @command(0x8006, handshake=True)
    def wipe(self, apdu: CommandApdu) -> bytes:
        self.card.wipe()
        return b""

    @command(0x8007)
    def read_pin_counter(self, apdu: CommandApdu) -> bytes:
        return bytes((self.card.pin_counter,))

    @command(0x8008)
    def read_success_log(self, apdu: CommandApdu) -> bytes:
        return self.card.success_log

    @command(0x8009)
    def read_failure_logs(self, apdu: CommandApdu) -> bytes:
        return b"".join(self.card.failure_logs)

    @command(0x800A, auth=True)
    def read_seed_metadata(self, apdu: CommandApdu) -> bytes:
        return self.card.seed_metadata

    @command(0x800B, auth=True, data_len=SEED_METADATA_LEN)
    def write_seed_metadata(self, apdu: CommandApdu) -> bytes:
        self.card.seed_metadata = apdu.data
        return b""

    @command(0x800C, auth=True)
    def read_seed(self, apdu: CommandApdu) -> bytes:
        if self.card.seed is None:
            # Not specified by the card API yet (open item); card OS 0.2.0
            # answers with an internal error.
            raise CardError(SW.COMMAND_INTERNAL_ERROR)
        return self.card.seed

    @command(0x800D, auth=True, data_len=SEED_LEN)
    def write_seed(self, apdu: CommandApdu) -> bytes:
        self.card.seed = apdu.data
        return b""


def tap_over_debuglink(debug: DebugLink, card: K1N1Tag) -> None:
    """Tap `card` to the emulator and answer its NFC exchanges.

    Returns once the device ends the NFC session.
    """
    with card as activation:
        uid = next(activation)
        debug.k1n1_tap(
            uid,
            lambda data, is_psk: activation.send(PskShare(data) if is_psk else data),
        )
