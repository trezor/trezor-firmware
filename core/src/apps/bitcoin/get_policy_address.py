from typing import TYPE_CHECKING
from ubinascii import unhexlify

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import Address, GetPolicyAddress

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def get_policy_address(
    msg: GetPolicyAddress, keychain: Keychain, coin: CoinInfo
) -> Address:
    from ubinascii import hexlify

    from trezor import protobuf
    from trezor.crypto import bip32, hashlib, hmac
    from trezor.messages import Address
    from trezor.ui.layouts import show_address
    from trezor.wire import DataError

    from .addresses import ecdsa_hash_pubkey, encode_bech32_address

    key = keychain.derive_slip21([b"SLIP-0019", b"Trezor-Policy"]).key()

    new_buffer = bytearray(protobuf.encoded_length(msg.policy))
    protobuf.encode(new_buffer, msg.policy)
    encoded_policy = bytes(new_buffer)
    policy_mac = hmac(hmac.SHA256, key, encoded_policy).digest()

    if policy_mac != msg.mac:
        raise DataError("Invalid MAC")

    # Deserialize xpubs
    # Bitcoin mainnet xpub version: 0x0488b21e, testnet: 0x043587cf
    xpub_version = 0x0488B21E if coin.coin_name == "Bitcoin" else 0x043587CF
    node1 = bip32.deserialize_public(msg.policy.xpubs[0], xpub_version, coin.curve_name)

    node1.derive(int(msg.change), True)
    node1.derive(msg.index + 1, True)
    pk1 = node1.public_key()
    print(f"pk1: {hexlify(pk1)}")
    # pk1 = unhexlify(
    #     "02eea9b8b00157bf77dad9225948a4c95cdbb30099688bf35017ae7ec03c883829"
    # )

    node2 = bip32.deserialize_public(msg.policy.xpubs[1], xpub_version, coin.curve_name)
    node2.derive(int(msg.change), True)
    node2.derive(msg.index + 1, True)
    pk2 = node2.public_key()
    print(f"pk2: {hexlify(pk2)}")
    pk2_hash = ecdsa_hash_pubkey(pk2, coin)
    print(f"pk2_hash: {hexlify(pk2_hash)}")
    # pk2_hash = ecdsa_hash_pubkey(unhexlify(
    #     "03c8166eb40ac84088b618ec07c7cebadacee31c5f5b04a1e8c2a2f3e748eb2cdd"
    # ), coin)

    # Build the witness script
    assert msg.policy.blocks <= 16
    script = (
        b"\x21"  # OP_PUSHBYTES_33
        + pk1
        + b"\xac\x73\x64\x76\xa9\x14"  # OP_CHECKSIG OP_IFDUP OP_NOTIF OP_DUP OP_HASH160 OP_PUSHBYTES_20
        + pk2_hash  # pk2_hash (20 bytes)
        + b"\x88\xad"  # OP_EQUALVERIFY OP_CHECKSIGVERIFY
        + bytes([0x50 + msg.policy.blocks])  # OP_1 to OP_16
        + b"\xb2\x68"  # OP_CSV OP_ENDIF
    )
    print(f"script: {hexlify(script)}")

    # Hash the witness script with SHA256
    witness_script_hash = hashlib.sha256(script).digest()

    # Create P2WSH address
    assert coin.bech32_prefix is not None
    address = encode_bech32_address(coin.bech32_prefix, 0, witness_script_hash)

    if msg.show_display:
        await show_address(
            address,
            title=msg.policy.name,
            network=coin.coin_name,
            br_name="/bitcoin/miniscript/get_policy_address",
        )

    return Address(address=address)


def get_push_number_hex(n: int) -> str:
    """
    Encodes a positive integer (1-65535) into Bitcoin Script hex.

    Raises:
        ValueError: If n <= 0 or n > 65535.
    """
    from ubinascii import hexlify, unhexlify

    if n <= 0:
        raise ValueError("Input must be strictly positive (greater than 0).")
    if n > 65535:
        raise ValueError("Input must be 65535 or less.")

    # Handle Small Numbers (OP_1 to OP_16)
    if n <= 16:
        # 0x51 is OP_1, 0x60 is OP_16
        return hexlify(0x50 + n)[2:]

    # Handle General Numbers (17 - 65535)
    # Calculate minimum bytes needed to represent the number
    length = (n.bit_length() + 7) // 8
    data = bytearray(n.to_bytes(length, "little"))

    # Check the Most Significant Bit (MSB) of the last byte.
    # If it is 1 (e.g. 0x80), Bitcoin will interpret it as negative.
    # We must append a 0x00 byte to keep it positive.
    if data[-1] & 0x80:
        data.append(0x00)

    # Since the max is 65535, the resulting byte length will never exceed 3.
    # We can simply use the length as the opcode (e.g., 01, 02, 03).
    return f"{len(data):02x}" + data
