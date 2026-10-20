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

"""Boot command and arguments, as the emulator reports them on exit.

Mirrors ``core/embed/sys/startup/inc/sys/bootargs.h``. The unix build writes
``trezor.bootargs`` into the profile directory on every exit; the bootloader
emulator reads a file of the same format with ``-B``.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

# BOOT_ARGS_MAX_SIZE in bootargs.h
BOOT_ARGS_MAX_SIZE = 256 - 8

# bootargs_file_t in core/embed/sys/startup/unix/bootutils.c
_FILE = struct.Struct(f"<Q{BOOT_ARGS_MAX_SIZE}s")

_CSTR64 = 64


class BootCommand(IntEnum):
    """boot_command_t"""

    NONE = 0x00000000
    STOP_AND_WAIT = 0x0FC35A96
    STOP_AND_CONNECT = 0x3B7E1C64
    INSTALL_UPGRADE = 0xFA4A5C8D
    SHOW_RSOD = 0x7CD945A0
    WIPE = 0xD965CE36
    REBOOT = 0xA5C3D4E2
    POWER_OFF = 0x24EEE8828


class TermReason(IntEnum):
    """systask_term_reason_t"""

    EXIT = 0
    ERROR = 1
    FATAL = 2
    FAULT = 3


def _cstr(data: bytes) -> str:
    return data.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def _cbytes(text: str, size: int) -> bytes:
    encoded = text.encode()
    if len(encoded) >= size:
        raise ValueError(f"string does not fit into {size} bytes: {text!r}")
    return encoded.ljust(size, b"\0")


@dataclass(frozen=True)
class WipeInfo:
    """bootutils_wipe_info_t: what the bootloader shows after a wipe."""

    title: str
    message: str
    footer: str = ""

    SIZE = 3 * _CSTR64

    @classmethod
    def parse(cls, data: bytes) -> WipeInfo:
        return cls(
            title=_cstr(data[0:64]),
            message=_cstr(data[64:128]),
            footer=_cstr(data[128:192]),
        )

    def to_bytes(self) -> bytes:
        return (
            _cbytes(self.title, 64)
            + _cbytes(self.message, 64)
            + _cbytes(self.footer, 64)
        )


@dataclass(frozen=True)
class SystemFault:
    """system_fault_t, in the layout of the unix build (no secure-fault
    registers, stack pointer limit present)."""

    irqn: int
    cfsr: int
    hfsr: int
    mmfar: int
    bfar: int
    pc: int
    sp: int
    sp_lim: int

    _STRUCT = struct.Struct("<iIIIIIII")

    @classmethod
    def parse(cls, data: bytes) -> SystemFault:
        return cls(*cls._STRUCT.unpack_from(data))


@dataclass(frozen=True)
class PostMortem:
    """systask_postmortem_t: why a task ended.

    Exactly one of ``exit_code``, ``fault``, ``fatal`` or ``error`` is set,
    according to ``reason``.
    """

    reason: TermReason
    privileged: bool
    exit_code: int | None = None
    fault: SystemFault | None = None
    # (line, file, expression)
    fatal: tuple[int, str, str] | None = None
    # (title, message, footer)
    error: tuple[str, str, str] | None = None

    # reason (int32), privileged (bool), padding; the union starts at 8
    _HEAD = struct.Struct("<i?3x")
    UNION_OFFSET = 8

    @classmethod
    def parse(cls, data: bytes) -> PostMortem:
        reason_value, privileged = cls._HEAD.unpack_from(data)
        reason = TermReason(reason_value)
        body = data[cls.UNION_OFFSET :]
        if reason is TermReason.EXIT:
            return cls(reason, privileged, exit_code=struct.unpack_from("<i", body)[0])
        if reason is TermReason.FAULT:
            return cls(reason, privileged, fault=SystemFault.parse(body))
        if reason is TermReason.FATAL:
            line = struct.unpack_from("<i", body)[0]
            return cls(
                reason,
                privileged,
                fatal=(line, _cstr(body[4:68]), _cstr(body[68:132])),
            )
        return cls(
            reason,
            privileged,
            error=(_cstr(body[0:64]), _cstr(body[64:128]), _cstr(body[128:192])),
        )

    @classmethod
    def from_error(
        cls, title: str, message: str, footer: str = "", privileged: bool = True
    ) -> PostMortem:
        return cls(TermReason.ERROR, privileged, error=(title, message, footer))

    def to_bytes(self) -> bytes:
        head = self._HEAD.pack(self.reason, self.privileged)
        if self.reason is TermReason.ERROR:
            assert self.error is not None
            title, message, footer = self.error
            body = _cbytes(title, 64) + _cbytes(message, 64) + _cbytes(footer, 64)
        elif self.reason is TermReason.EXIT:
            body = struct.pack("<i", self.exit_code or 0)
        elif self.reason is TermReason.FATAL:
            assert self.fatal is not None
            line, file, expr = self.fatal
            body = struct.pack("<i", line) + _cbytes(file, 64) + _cbytes(expr, 64)
        else:
            raise NotImplementedError("fault records are only decoded")
        return head + body


@dataclass(frozen=True)
class BootArgs:
    """The boot command with its raw argument block."""

    command: int
    args: bytes = b"\0" * BOOT_ARGS_MAX_SIZE

    def __post_init__(self) -> None:
        if len(self.args) > BOOT_ARGS_MAX_SIZE:
            raise ValueError("boot args too long")
        if len(self.args) < BOOT_ARGS_MAX_SIZE:
            object.__setattr__(self, "args", self.args.ljust(BOOT_ARGS_MAX_SIZE, b"\0"))

    @property
    def command_name(self) -> str:
        try:
            return BootCommand(self.command).name
        except ValueError:
            return f"0x{self.command:X}"

    # typed views of the argument block

    @property
    def upgrade_hash(self) -> bytes | None:
        if self.command == BootCommand.INSTALL_UPGRADE:
            return self.args[:32]
        return None

    @property
    def wipe_info(self) -> WipeInfo | None:
        if self.command == BootCommand.WIPE:
            return WipeInfo.parse(self.args)
        return None

    @property
    def postmortem(self) -> PostMortem | None:
        if self.command == BootCommand.SHOW_RSOD:
            return PostMortem.parse(self.args)
        return None

    # constructors

    @classmethod
    def none(cls) -> BootArgs:
        return cls(BootCommand.NONE)

    @classmethod
    def stop_and_wait(cls) -> BootArgs:
        return cls(BootCommand.STOP_AND_WAIT)

    @classmethod
    def install_upgrade(cls, header_hash: bytes) -> BootArgs:
        if len(header_hash) != 32:
            raise ValueError("header hash must be 32 bytes")
        return cls(BootCommand.INSTALL_UPGRADE, header_hash)

    @classmethod
    def wipe(cls, info: WipeInfo) -> BootArgs:
        return cls(BootCommand.WIPE, info.to_bytes())

    @classmethod
    def show_rsod(cls, pminfo: PostMortem) -> BootArgs:
        return cls(BootCommand.SHOW_RSOD, pminfo.to_bytes())

    # file format

    @classmethod
    def parse(cls, data: bytes) -> BootArgs:
        if len(data) != _FILE.size:
            raise ValueError(f"expected {_FILE.size} bytes, got {len(data)}")
        command, args = _FILE.unpack(data)
        return cls(command, args)

    @classmethod
    def from_file(cls, path: Path | str) -> BootArgs:
        return cls.parse(Path(path).read_bytes())

    def to_bytes(self) -> bytes:
        return _FILE.pack(self.command, self.args)

    def write(self, path: Path | str) -> Path:
        path = Path(path)
        path.write_bytes(self.to_bytes())
        return path
