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

import hashlib
import hmac
import json
import os
from typing import Tuple
from urllib.parse import urlparse

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from trezorlib import misc, ui
from trezorlib.client import TrezorClient
from trezorlib.tools import parse_path
from trezorlib.transport import get_transport

# Return path by BIP-32
BIP32_PATH = parse_path("10016h/0")


# Deriving master key
def getMasterKey(client: TrezorClient) -> str:
    bip32_path = BIP32_PATH
    ENC_KEY = "Activate TREZOR Password Manager?"
    ENC_VALUE = bytes.fromhex(
        "2d650551248d792eabf628f451200d7f51cb63e46aadcbb1038aacb05e8c8aee2d650551248d792eabf628f451200d7f51cb63e46aadcbb1038aacb05e8c8aee"
    )
    key = misc.encrypt_keyvalue(client, bip32_path, ENC_KEY, ENC_VALUE, True, True)
    return key.hex()


# Deriving file name and encryption key
def getFileEncKey(key: str) -> Tuple[str, str, str]:
    filekey, enckey = key[: len(key) // 2], key[len(key) // 2 :]
    FILENAME_MESS = b"5f91add3fa1c3c76e90c90a3bd0999e2bd7833d06a483fe884ee60397aca277a"
    digest = hmac.new(str.encode(filekey), FILENAME_MESS, hashlib.sha256).hexdigest()
    filename = digest + ".pswd"
    return (filename, filekey, enckey)


# File level decryption and file reading
def decryptStorage(path: str, key: str) -> dict:
    cipherkey = bytes.fromhex(key)
    with open(path, "rb") as f:
        iv = f.read(12)
        tag = f.read(16)
        cipher = Cipher(
            algorithms.AES(cipherkey), modes.GCM(iv, tag), backend=default_backend()
        )
        decryptor = cipher.decryptor()
        data: str = ""
        while True:
            block = f.read(16)
            # data are not authenticated yet
            if block:
                data = data + decryptor.update(block).decode()
            else:
                break
        # throws exception when the tag is wrong
        data = data + decryptor.finalize().decode()
    return json.loads(data)


def decryptEntryValue(nonce: str, val: bytes) -> dict:
    cipherkey = bytes.fromhex(nonce)
    iv = val[:12]
    tag = val[12:28]
    cipher = Cipher(
        algorithms.AES(cipherkey), modes.GCM(iv, tag), backend=default_backend()
    )
    decryptor = cipher.decryptor()
    data: str = ""
    inputData = val[28:]
    while True:
        block = inputData[:16]
        inputData = inputData[16:]
        if block:
            data = data + decryptor.update(block).decode()
        else:
            break
        # throws exception when the tag is wrong
    data = data + decryptor.finalize().decode()
    return json.loads(data)


# Decrypt give entry nonce
def getDecryptedNonce(client: TrezorClient, entry: dict) -> str:
    print()
    print("Waiting for Trezor input ...")
    print()
    if "item" in entry:
        item = entry["item"]
    else:
        item = entry["title"]

    pr = urlparse(item)
    if pr.scheme and pr.netloc:
        item = pr.netloc

    ENC_KEY = f"Unlock {item} for user {entry['username']}?"
    ENC_VALUE = entry["nonce"]
    decrypted_nonce = misc.decrypt_keyvalue(
        client, BIP32_PATH, ENC_KEY, bytes.fromhex(ENC_VALUE), False, True
    )
    return decrypted_nonce.hex()


# Pretty print of list
def printEntries(entries: dict) -> None:
    print("Password entries")
    print("================")
    print()
    for k, v in entries.items():
        print(f"Entry id: #{k}")
        print("-------------")
        for kk, vv in v.items():
            if kk in ["nonce", "safe_note", "password"]:
                continue  # skip these fields
            print("*", kk, ": ", vv)
        print()


def main() -> None:
    try:
        transport = get_transport()
    except Exception as e:
        print(e)
        return

    client = TrezorClient(transport=transport, ui=ui.ClickUI())

    print()
    print("Confirm operation on Trezor")
    print()

    masterKey = getMasterKey(client)
    # print('master key:', masterKey)

    fileName = getFileEncKey(masterKey)[0]
    # print('file name:', fileName)

    home = os.path.expanduser("~")
    path = os.path.join(home, "Dropbox", "Apps", "TREZOR Password Manager")
    # print('path to file:', path)

    encKey = getFileEncKey(masterKey)[2]
    # print('enckey:', encKey)

    full_path = os.path.join(path, fileName)
    parsed_json = decryptStorage(full_path, encKey)

    # list entries
    entries = parsed_json["entries"]
    printEntries(entries)

    entry_id = input("Select entry number to decrypt: ")
    entry_id = str(entry_id)

    plain_nonce = getDecryptedNonce(client, entries[entry_id])

    pwdArr = entries[entry_id]["password"]["data"]
    pwdHex = "".join([hex(x)[2:].zfill(2) for x in pwdArr])
    print("password: ", decryptEntryValue(plain_nonce, bytes.fromhex(pwdHex)))

    safeNoteArr = entries[entry_id]["safe_note"]["data"]
    safeNoteHex = "".join([hex(x)[2:].zfill(2) for x in safeNoteArr])
    print("safe_note:", decryptEntryValue(plain_nonce, bytes.fromhex(safeNoteHex)))


if __name__ == "__main__":
    main()
