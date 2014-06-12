#!/usr/bin/python

'''
Use Trezor as a hardware key for opening EncFS filesystem!

Demo usage:

encfs --standard --extpass=./encfs_aes_getpass.py ~/.crypt ~/crypt
'''

import os
import sys
import json
import base64
import hashlib
import binascii

from trezorlib.client import TrezorClient, TrezorClientDebug
from trezorlib.transport_hid import HidTransport

def wait_for_devices():
    devices = HidTransport.enumerate()
    while not len(devices):
        sys.stderr.write("Please connect Trezor to computer and press Enter...")
        raw_input()
        devices = HidTransport.enumerate()

    return devices

def choose_device(devices):
    i = 0
    sys.stderr.write("----------------------------\n")
    sys.stderr.write("Available devices:\n")
    for d in devices:
        try:
            t = HidTransport(d)
        except IOError:
            sys.stderr.write("[-] <device is currently in use>\n")
            continue

        client = TrezorClient(t)

        if client.features.label:
            sys.stderr.write("[%d] %s\n" % (i, client.features.label))
        else:
            sys.stderr.write("[%d] <no label>\n" % i)
        t.close()
        i += 1

    sys.stderr.write("----------------------------\n")
    sys.stderr.write("Please choose device to use: ")

    try:
        device_id = int(raw_input())
        transport = HidTransport(devices[device_id])
    except:
        raise Exception("Invalid choice, exiting...")

    return transport

def main():

    devices = wait_for_devices()

    if len(devices) > 1:
        transport = choose_device(devices)
    else:
        transport = HidTransport(devices[0])

    client = TrezorClient(transport)

    rootdir = os.environ['encfs_root']  # Read "man encfs" for more
    passw_file = os.path.join(rootdir, 'password.dat')

    if os.path.exists(passw_file):
        # Existing encfs drive, let's load password

        sys.stderr.write('Please confirm action on your device.\n')
        label, passw_encrypted, bip32_path = open(passw_file, 'r').read().split(',')
        passw = client.decrypt_keyvalue(json.loads(binascii.unhexlify(bip32_path)),
                    binascii.unhexlify(label),
                    binascii.unhexlify(passw_encrypted),
                    False, True)
        print passw

    else:
        # New encfs drive, let's generate password

        sys.stderr.write('Please provide label for new drive: ')
        label = raw_input()

        sys.stderr.write('Computer asked Trezor for new strong password.\nPlease confirm action on your device.\n')

        # 32 bytes, good for AES
        trezor_entropy = client.get_entropy(32)
        urandom_entropy = os.urandom(32)
        passw = hashlib.sha256(trezor_entropy + urandom_entropy).digest()

        if len(passw) != 32:
            raise Exception("32 bytes password expected")

        bip32_path = [10, 0]
        passw_encrypted = client.encrypt_keyvalue(bip32_path,
                    label, passw, False, True)

        f = open(passw_file, 'wb')
        f.write(binascii.hexlify(label) + ',' + binascii.hexlify(passw_encrypted) + \
            ',' + binascii.hexlify(json.dumps(bip32_path)))
        f.close()

        print passw

if __name__ == '__main__':
    main()
