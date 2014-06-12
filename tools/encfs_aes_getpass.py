#!/usr/bin/python

'''
Use Trezor as a hardware key for opening EncFS filesystem!

Demo usage:

encfs --standard --extpass=./encfs_aes_getpass.py ~/.crypt ~/crypt
'''

import os
import sys
import base64
import binascii

from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport

def wait_for_devices():
    devices = HidTransport.enumerate()
    while not len(devices):
        sys.stderr.write("Please connect Trezor to computer and press Enter...")
        raw_input()
        devices = HidTransport.enumerate()

    return devices

def list_devices(devices):
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
    sys.stderr.write("Please choice device to use: ")

    try:
        device_id = int(raw_input())
        HidTransport(devices[device_id])
    except:
        raise Exception("Invalid choice, exiting...")

    return device_id

def main():

    devices = wait_for_devices()

    if len(devices) > 1:
        device_id = list_devices(devices)
    else:
        device_id = 0

    transport = HidTransport(devices[device_id])
    client = TrezorClient(transport)

    rootdir = os.environ['encfs_root']  # Read "man encfs" for more
    passw_file = os.path.join(rootdir, 'password.dat')

    if os.path.exists(passw_file):
        # Existing encfs drive, let's load password

        label, passw_encrypted = open(passw_file, 'r').read().split(',')
        passw = client.decrypt_keyvalue([10, 0],
                    binascii.unhexlify(label),
                    binascii.unhexlify(passw_encrypted),
                    False, True)
        print passw

    else:
        # New encfs drive, let's generate password

        sys.stderr.write('Please provide label for new drive: ')
        label = raw_input()

        passw = base64.b64encode(os.urandom(24))  # 32 bytes in base64, good for AES

        if len(passw) != 32:
            raise Exception("32 bytes password expected")

        passw_encrypted = client.encrypt_keyvalue([10, 0],
                    label, passw, False, True)

        f = open(passw_file, 'wb')
        f.write(binascii.hexlify(label) + ',' + binascii.hexlify(passw_encrypted))
        f.close()

        print passw

if __name__ == '__main__':
    main()
