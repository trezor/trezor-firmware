#!/usr/bin/env python3
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import hmac
import hashlib
import json
import os
from urllib.parse import urlparse

from trezorlib.client import TrezorClient
from trezorlib.transport import get_transport
from trezorlib.tools import parse_path


# Return path by BIP-32
BIP32_PATH = parse_path("10016h/0")


# Deriving master key
def getMasterKey(client):
    bip32_path = BIP32_PATH
    ENC_KEY = 'Activate TREZOR Password Manager?'
    ENC_VALUE = bytes.fromhex('2d650551248d792eabf628f451200d7f51cb63e46aadcbb1038aacb05e8c8aee2d650551248d792eabf628f451200d7f51cb63e46aadcbb1038aacb05e8c8aee')
    key = client.encrypt_keyvalue(
        bip32_path,
        ENC_KEY,
        ENC_VALUE,
        True,
        True
    )
    return key.hex()


# Deriving file name and encryption key
def getFileEncKey(key):
    filekey, enckey = key[:len(key) // 2], key[len(key) // 2:]
    FILENAME_MESS = b'5f91add3fa1c3c76e90c90a3bd0999e2bd7833d06a483fe884ee60397aca277a'
    digest = hmac.new(filekey, FILENAME_MESS, hashlib.sha256).hexdigest()
    filename = digest + '.pswd'
    return [filename, filekey, enckey]


# File level decryption and file reading
def decryptStorage(path, key):
    cipherkey = bytes.fromhex(key)
    with open(path, 'rb') as f:
        iv = f.read(12)
        tag = f.read(16)
        cipher = Cipher(algorithms.AES(cipherkey), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        data = ''
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


def decryptEntryValue(nonce, val):
    cipherkey = bytes.fromhex(nonce)
    iv = val[:12]
    tag = val[12:28]
    cipher = Cipher(algorithms.AES(cipherkey), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    data = ''
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
def getDecryptedNonce(client, entry):
    print()
    print('Waiting for TREZOR input ...')
    print()
    if 'item' in entry:
        item = entry['item']
    else:
        item = entry['title']

    pr = urlparse(item)
    if pr.scheme and pr.netloc:
        item = pr.netloc

    ENC_KEY = 'Unlock %s for user %s?' % (item, entry['username'])
    ENC_VALUE = entry['nonce']
    decrypted_nonce = client.decrypt_keyvalue(
        BIP32_PATH,
        ENC_KEY,
        bytes.fromhex(ENC_VALUE),
        False,
        True
    )
    return decrypted_nonce.hex()


# Pretty print of list
def printEntries(entries):
    print('Password entries')
    print('================')
    print()
    for k, v in entries.items():
        print('Entry id: #%s' % k)
        print('-------------')
        for kk, vv in v.items():
            if kk in ['nonce', 'safe_note', 'password']:
                continue  # skip these fields
            print('*', kk, ': ', vv)
        print()
    return


def main():
    try:
        transport = get_transport()
    except Exception as e:
        print(e)
        return

    client = TrezorClient(transport)

    print()
    print('Confirm operation on TREZOR')
    print()

    masterKey = getMasterKey(client)
    # print('master key:', masterKey)

    fileName = getFileEncKey(masterKey)[0]
    # print('file name:', fileName)

    path = os.path.expanduser('~/Dropbox/Apps/TREZOR Password Manager/')
    # print('path to file:', path)

    encKey = getFileEncKey(masterKey)[2]
    # print('enckey:', encKey)

    full_path = path + fileName
    parsed_json = decryptStorage(full_path, encKey)

    # list entries
    entries = parsed_json['entries']
    printEntries(entries)

    entry_id = input('Select entry number to decrypt: ')
    entry_id = str(entry_id)

    plain_nonce = getDecryptedNonce(client, entries[entry_id])

    pwdArr = entries[entry_id]['password']['data']
    pwdHex = ''.join([hex(x)[2:].zfill(2) for x in pwdArr])
    print('password: ', decryptEntryValue(plain_nonce, bytes.fromhex(pwdHex)))

    safeNoteArr = entries[entry_id]['safe_note']['data']
    safeNoteHex = ''.join([hex(x)[2:].zfill(2) for x in safeNoteArr])
    print('safe_note:', decryptEntryValue(plain_nonce, bytes.fromhex(safeNoteHex)))

    return


if __name__ == '__main__':
    main()
