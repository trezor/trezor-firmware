#!/usr/bin/env python3
from trezorlib.client import get_default_client
from trezorlib.tools import parse_path
from trezorlib import btc


def main():
    # Use first connected device
    client = get_default_client()

    # Print out Trezor's features and settings
    print(client.features)

    # Get the first address of first BIP44 account
    bip32_path = parse_path("44'/0'/0'/0/0")
    address = btc.get_address(client, "Bitcoin", bip32_path, True)
    print("Bitcoin address:", address)


if __name__ == "__main__":
    main()
