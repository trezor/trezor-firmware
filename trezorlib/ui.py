import os

import click
from mnemonic import Mnemonic

from . import device
from .exceptions import Cancelled
from .messages import PinMatrixRequestType, WordRequestType

PIN_MATRIX_DESCRIPTION = """
Use the numeric keypad to describe number positions. The layout is:
    7 8 9
    4 5 6
    1 2 3
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


def echo(*args, **kwargs):
    return click.echo(*args, err=True, **kwargs)


def prompt(*args, **kwargs):
    return click.prompt(*args, err=True, **kwargs)


class ClickUI:
    @staticmethod
    def button_request(code):
        echo("Please confirm action on your Trezor device")

    @staticmethod
    def get_pin(code=None):
        if code == PIN_CURRENT:
            desc = "current PIN"
        elif code == PIN_NEW:
            desc = "new PIN"
        elif code == PIN_CONFIRM:
            desc = "new PIN again"
        else:
            desc = "PIN"
            echo(PIN_MATRIX_DESCRIPTION)

        while True:
            pin = prompt("Please enter {}".format(desc), hide_input=True)
            if not pin.isdigit():
                echo("Non-numerical PIN provided, please try again")
            else:
                return pin

    @staticmethod
    def get_passphrase():
        if os.getenv("PASSPHRASE") is not None:
            echo("Passphrase required. Using PASSPHRASE environment variable.")
            return os.getenv("PASSPHRASE")

        while True:
            passphrase = prompt("Passphrase required", hide_input=True)
            second = prompt("Confirm your passphrase", hide_input=True)
            if passphrase == second:
                return passphrase
            else:
                echo("Passphrase did not match. Please try again.")


def mnemonic_words(expand=False, language="english"):
    if expand:
        wordlist = Mnemonic(language).wordlist
    else:
        wordlist = set()

    def expand_word(word):
        if not expand:
            return word
        if word in wordlist:
            return word
        matches = [w for w in wordlist if w.startswith(word)]
        if len(matches) == 1:
            return word
        echo("Choose one of: " + ", ".join(matches))
        raise KeyError(word)

    def get_word(type):
        assert type == WordRequestType.Plain
        while True:
            try:
                word = prompt("Enter one word of mnemonic")
                return expand_word(word)
            except KeyError:
                pass
            except (KeyboardInterrupt, click.Abort):
                raise Cancelled from None

    return get_word


def matrix_words(type):
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
