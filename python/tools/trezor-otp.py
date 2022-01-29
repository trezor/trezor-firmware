#!/usr/bin/env python3

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

import configparser
import os
import re
import sys

import pyotp
from trezorlib.client import TrezorClient
from trezorlib.misc import decrypt_keyvalue, encrypt_keyvalue
from trezorlib.tools import parse_path
from trezorlib.transport import get_transport
from trezorlib.ui import ClickUI

BIP32_PATH = parse_path("10016h/0")


def encrypt(type: str, domain: str, secret: str) -> str:
    transport = get_transport()
    client = TrezorClient(transport, ClickUI())
    dom = type.upper() + ": " + domain
    enc = encrypt_keyvalue(client, BIP32_PATH, dom, secret.encode(), False, True)
    client.close()
    return enc.hex()


def decrypt(type: str, domain: str, secret: bytes) -> bytes:
    transport = get_transport()
    client = TrezorClient(transport, ClickUI())
    dom = type.upper() + ": " + domain
    dec = decrypt_keyvalue(client, BIP32_PATH, dom, secret, False, True)
    client.close()
    return dec


class Config:
    def __init__(self) -> None:
        XDG_CONFIG_HOME = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        os.makedirs(XDG_CONFIG_HOME, exist_ok=True)
        self.filename = XDG_CONFIG_HOME + "/trezor-otp.ini"
        self.config = configparser.ConfigParser()
        self.config.read(self.filename)

    def add(self, domain: str, secret: str, type: str = "totp") -> None:
        self.config[domain] = {}
        self.config[domain]["secret"] = encrypt(type, domain, secret)
        self.config[domain]["type"] = type
        if type == "hotp":
            self.config[domain]["counter"] = "0"
        with open(self.filename, "w") as f:
            self.config.write(f)

    def get(self, domain: str):
        s = self.config[domain]
        if s["type"] == "hotp":
            s["counter"] = str(int(s["counter"]) + 1)
            with open(self.filename, "w") as f:
                self.config.write(f)
        secret = decrypt(s["type"], domain, bytes.fromhex(s["secret"]))
        if s["type"] == "totp":
            return pyotp.TOTP(secret).now()
        if s["type"] == "hotp":
            c = int(s["counter"])
            return pyotp.HOTP(secret).at(c)
        return ValueError("unknown domain or type")


def add() -> None:
    c = Config()
    domain = input("domain: ")
    while True:
        secret = input("secret: ")
        if re.match(r"^[A-Z2-7]{16}$", secret):
            break
        print("invalid secret")
    while True:
        type = input("type (t=totp h=hotp): ")
        if type in ("t", "h"):
            break
        print("invalid type")
    c.add(domain, secret, type + "otp")
    print("Entry added")


def get(domain: str) -> None:
    c = Config()
    s = c.get(domain)
    print(s)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: trezor-otp.py [add|domain]")
        sys.exit(1)
    if sys.argv[1] == "add":
        add()
    else:
        get(sys.argv[1])


if __name__ == "__main__":
    main()
