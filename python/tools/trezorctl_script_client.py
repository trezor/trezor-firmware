"""
Reference client implementation consuming trezorctl's script interface
(ScriptUI class) available by using `--script` flag in any trezorctl command.

Function `get_address()` is showing the communication with ScriptUI
on a specific example
"""

import os
import subprocess
from typing import Dict, List, Optional, Tuple, Union

import click


def parse_args_from_line(line: str) -> Tuple[str, Dict[str, Union[str, bool]]]:
    # ?PIN code=123
    # ?PASSPHRASE available_on_device
    command, *args = line.split(" ")
    result: Dict[str, Union[str, bool]] = {}
    for arg in args:
        if "=" in arg:
            key, value = arg.split("=")
            result[key] = value
        else:
            result[arg] = True
    return command, result


def get_pin_from_user(code: Optional[str] = None) -> str:
    # ?PIN
    # ?PIN code=Current
    while True:
        try:
            pin = click.prompt(
                f"Enter PIN (code: {code})",
                hide_input=True,
                default="",
                show_default=False,
            )
        except click.Abort:
            return "CANCEL"
        if not all(c in "123456789" for c in pin):
            click.echo("PIN must only be numbers 1-9")
            continue
        return ":" + pin


def show_button_request(
    code: Optional[str] = None, pages: Optional[str] = None, name: Optional[str] = None
) -> None:
    # ?BUTTON code=Other
    # ?BUTTON code=SignTx pages=2
    # ?BUTTON code=ProtectCall name=confirm_set_pin
    print(f"Please confirm action on Trezor (code={code} name={name} pages={pages})")


def get_passphrase_from_user(available_on_device: bool = False) -> str:
    # ?PASSPHRASE
    # ?PASSPHRASE available_on_device
    if available_on_device:
        if click.confirm("Enter passphrase on device?", default=True):
            return "ON_DEVICE"

    env_passphrase = os.getenv("PASSPHRASE")
    if env_passphrase:
        if click.confirm("Use env PASSPHRASE?", default=False):
            return ":" + env_passphrase

    while True:
        try:
            passphrase = click.prompt("Enter passphrase", hide_input=True, default="")
        except click.Abort:
            return "CANCEL"

        passphrase2 = click.prompt(
            "Enter passphrase again", hide_input=True, default=""
        )
        if passphrase != passphrase2:
            click.echo("Passphrases do not match")
            continue
        return ":" + passphrase


def get_address() -> str:
    args = """
        trezorctl --script get-address -n "m/49h/0h/0h/0/0"
    """.strip()
    p = subprocess.Popen(  # type: ignore [No overloads for "__new__" match the provided arguments]
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        shell=True,
        bufsize=0,
    )

    assert p.stdout is not None
    assert p.stdin is not None

    text_result: List[str] = []
    while True:
        line = p.stdout.readline().strip()
        if not line:
            break

        if line.startswith("?"):
            command, args = parse_args_from_line(line)
            if command == "?PIN":
                response = get_pin_from_user(**args)
                p.stdin.write(response + "\n")
            elif command == "?PASSPHRASE":
                response = get_passphrase_from_user(**args)
                p.stdin.write(response + "\n")
            elif command == "?BUTTON":
                show_button_request(**args)
            else:
                print("Unrecognized script command:", line)

        text_result.append(line)
        print(line)

    address = text_result[-1]
    print("Address:", address)
    return address


def clear_session_to_enable_pin():
    os.system("trezorctl clear-session")


if __name__ == "__main__":
    get_address()
    clear_session_to_enable_pin()
