# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import os
import sys
import typing as t

import click
from mnemonic import Mnemonic

from . import device, messages
from .client import MAX_PIN_LENGTH
from .exceptions import Cancelled, PinException
from .messages import Capability, PinMatrixRequestType, WordRequestType
from .transport.session import Session

PIN_MATRIX_DESCRIPTION = """
Use the numeric keypad or lowercase letters to describe number positions.

The layout is:

    7 8 9        e r t
    4 5 6  -or-  d f g
    1 2 3        c v b
""".strip()

RECOVERY_MATRIX_DESCRIPTION = """
Use the numeric keypad to describe positions.
For the word list use only left and right keys.
Use backspace to correct an entry.

The keypad layout is:
    7 8 9     7 | 9
    4 5 6     4 | 6
    1 2 3     1 | 3
""".strip()

PIN_GENERIC = None
PIN_CURRENT = PinMatrixRequestType.Current
PIN_NEW = PinMatrixRequestType.NewFirst
PIN_CONFIRM = PinMatrixRequestType.NewSecond
WIPE_CODE_NEW = PinMatrixRequestType.WipeCodeFirst
WIPE_CODE_CONFIRM = PinMatrixRequestType.WipeCodeSecond

# Workaround for limitation of Git Bash
# getpass function does not work correctly on Windows when not using a real terminal
# (the hidden input is not allowed and it also freezes the script completely)
# Details: https://bugs.python.org/issue44762
CAN_HANDLE_HIDDEN_INPUT = sys.stdin and sys.stdin.isatty()


def echo(*args: t.Any, **kwargs: t.Any) -> None:
    return click.echo(*args, err=True, **kwargs)


def prompt(text: str, *, hide_input: bool = False, **kwargs: t.Any) -> t.Any:
    # Disallowing hidden input and warning user when it would cause issues
    if not CAN_HANDLE_HIDDEN_INPUT and hide_input:
        hide_input = False
        text += " (WARNING: will be displayed!)"
    return click.prompt(text, hide_input=hide_input, err=True, **kwargs)


class ClickUI:
    def __init__(
        self, always_prompt: bool = False, passphrase_on_host: bool = False
    ) -> None:
        self.pinmatrix_shown = False
        self.last_prompt_shown = ""
        self.always_prompt = always_prompt
        self.passphrase_on_host = passphrase_on_host

    def _prompt_for_button(self, br: messages.ButtonRequest) -> str:
        if br.code == messages.ButtonRequestType.PassphraseEntry:
            return "Please enter passphrase on your Trezor device."
        if br.code == messages.ButtonRequestType.PinEntry:
            return "Please enter PIN on your Trezor device."

        return "Please confirm action on your Trezor device."

    def button_request(self, session: Session, br: messages.ButtonRequest) -> t.Any:
        prompt = self._prompt_for_button(br)
        if prompt != self.last_prompt_shown:
            echo(prompt)
        if not self.always_prompt:
            self.last_prompt_shown = prompt
        return session.call_raw(messages.ButtonAck())

    def get_pin(self, session: Session, request: messages.PinMatrixRequest) -> t.Any:
        code = request.type
        if code == PIN_CURRENT:
            desc = "current PIN"
        elif code == PIN_NEW:
            desc = "new PIN"
        elif code == PIN_CONFIRM:
            desc = "new PIN again"
        elif code == WIPE_CODE_NEW:
            desc = "new wipe code"
        elif code == WIPE_CODE_CONFIRM:
            desc = "new wipe code again"
        else:
            desc = "PIN"

        if not self.pinmatrix_shown:
            echo(PIN_MATRIX_DESCRIPTION)
            if not self.always_prompt:
                self.pinmatrix_shown = True

        while True:
            try:
                pin = prompt(f"Please enter {desc}", hide_input=True)
            except click.Abort:
                session.call_raw(messages.Cancel())
                raise Cancelled from None

            # translate letters to numbers if letters were used
            if all(d in "cvbdfgert" for d in pin):
                pin = pin.translate(str.maketrans("cvbdfgert", "123456789"))

            if any(d not in "123456789" for d in pin):
                echo(
                    "The value may only consist of digits 1 to 9 or letters cvbdfgert."
                )
            elif len(pin) > MAX_PIN_LENGTH:
                echo(f"The value must be at most {MAX_PIN_LENGTH} digits in length.")
            else:
                resp = session.call_raw(messages.PinMatrixAck(pin=pin))
                if isinstance(resp, messages.Failure) and resp.code in (
                    messages.FailureType.PinInvalid,
                    messages.FailureType.PinCancelled,
                    messages.FailureType.PinExpected,
                ):
                    raise PinException(resp.code, resp.message)
                else:
                    return resp

    def get_passphrase(
        self, session: Session, request: messages.PassphraseRequest
    ) -> t.Any:
        available_on_device = (
            Capability.PassphraseEntry in session.features.capabilities
        )
        if available_on_device and not self.passphrase_on_host:
            return session.call_raw(
                messages.PassphraseAck(passphrase=None, on_device=True)
            )

        env_passphrase = os.getenv("PASSPHRASE")
        if env_passphrase is not None:
            echo("Passphrase required. Using PASSPHRASE environment variable.")
            return session.call_raw(
                messages.PassphraseAck(passphrase=env_passphrase, on_device=False)
            )

        while True:
            try:
                passphrase = prompt(
                    "Passphrase required",
                    hide_input=True,
                    default="",
                    show_default=False,
                )
                # In case user sees the input on the screen, we do not need confirmation
                if not CAN_HANDLE_HIDDEN_INPUT:
                    break
                second = prompt(
                    "Confirm your passphrase",
                    hide_input=True,
                    default="",
                    show_default=False,
                )
                if passphrase == second:
                    break
                else:
                    echo("Passphrase did not match. Please try again.")
            except click.Abort:
                raise Cancelled from None

        return session.call_raw(
            messages.PassphraseAck(passphrase=passphrase, on_device=False)
        )


class ScriptUI:
    """Interface to be used by scripts, not directly by user.

    Communicates with a client application using print() and input().

    Lot of `ClickUI` logic is outsourced to the client application, which
    is responsible for supplying the PIN and passphrase.

    Reference client implementation can be found under `tools/trezorctl_script_client.py`.
    """

    @staticmethod
    def button_request(session: Session, br: messages.ButtonRequest) -> t.Any:
        code = br.code.name if br.code else None
        print(f"?BUTTON code={code} pages={br.pages} name={br.name}")
        return session.call_raw(messages.ButtonAck())

    @staticmethod
    def get_pin(session: Session, request: messages.PinMatrixRequest) -> t.Any:
        code = request.type
        if code is None:
            print("?PIN")
        else:
            print(f"?PIN code={code.name}")

        pin = input()
        if pin == "CANCEL":
            raise Cancelled from None
        elif not pin.startswith(":"):
            raise RuntimeError("Sent PIN must start with ':'")
        else:
            pin = pin[1:]
            resp = session.call_raw(messages.PinMatrixAck(pin=pin))
            if isinstance(resp, messages.Failure) and resp.code in (
                messages.FailureType.PinInvalid,
                messages.FailureType.PinCancelled,
                messages.FailureType.PinExpected,
            ):
                raise PinException(resp.code, resp.message)
            else:
                return resp

    @staticmethod
    def get_passphrase(session: Session, request: messages.PassphraseRequest) -> t.Any:
        available_on_device = (
            Capability.PassphraseEntry in session.features.capabilities
        )
        if available_on_device:
            print("?PASSPHRASE available_on_device")
        else:
            print("?PASSPHRASE")

        passphrase = input()
        if passphrase == "CANCEL":
            raise Cancelled from None
        elif passphrase == "ON_DEVICE":
            return session.call_raw(
                messages.PassphraseAck(passphrase=None, on_device=True)
            )
        elif not passphrase.startswith(":"):
            raise RuntimeError("Sent passphrase must start with ':'")
        else:
            passphrase = passphrase[1:]
            return session.call_raw(
                messages.PassphraseAck(passphrase=passphrase, on_device=False)
            )


def mnemonic_words(
    expand: bool = False, language: str = "english"
) -> t.Callable[[WordRequestType], str]:
    if expand:
        wordlist = Mnemonic(language).wordlist
    else:
        wordlist = []

    def expand_word(word: str) -> str:
        if not expand:
            return word
        if word in wordlist:
            return word
        matches = [w for w in wordlist if w.startswith(word)]
        if len(matches) == 1:
            return matches[0]
        echo("Choose one of: " + ", ".join(matches))
        raise KeyError(word)

    def get_word(type: WordRequestType) -> str:
        assert type == WordRequestType.Plain
        while True:
            try:
                word = prompt("Enter one word of mnemonic")
                return expand_word(word)
            except KeyError:
                pass
            except click.Abort:
                raise Cancelled from None

    return get_word


def matrix_words(type: WordRequestType) -> str:
    while True:
        try:
            ch = click.getchar()
        except (KeyboardInterrupt, EOFError):
            raise Cancelled from None

        if ch in "\x04\x1b":
            # Ctrl+D, Esc
            raise Cancelled
        if ch in "\x08\x7f":
            # Backspace, Del
            return device.RECOVERY_BACK
        if type == WordRequestType.Matrix6 and ch in "147369":
            return ch
        if type == WordRequestType.Matrix9 and ch in "123456789":
            return ch
