#!/usr/bin/python

from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport

def main():
    # List all connected TREZORs on USB
    devices = HidTransport.enumerate()

    # Use first connected device
    transport = HidTransport(devices[0])

    # Creates object for manipulating TREZOR
    client = TrezorClient(transport)

    # Print out TREZOR's features and settings
    print client.features

    # Get first address of first BIP44 account
    # (should be the same address as in mytrezor.com)
    bip32_path = client.expand_path("44'/0'/0'/0/0")
    address = client.get_address('Bitcoin', bip32_path, True)
    print 'Bitcoin address:', address

    client.close()

if __name__ == '__main__':
    main()
