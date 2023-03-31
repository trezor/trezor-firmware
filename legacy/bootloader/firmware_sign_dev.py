#!/usr/bin/env python3
import argparse
import hashlib
import struct

import ecdsa
from ecdsa import BadSignatureError

SLOTS = 3

pubkeys_dev = {
    1: "042c0b7cf95324a07d05398b240174dc0c2be444d96b159aa6c7f7b1e668680991ae31a9c671a36543f46cea8fce6984608aa316aa0472a7eed08847440218cb2f",
    2: "04edabbd16b41c8371b92ef2f04c1185b4f03b6dcd52ba9b78d9d7c89c8f2211452c88a66eb8ac3c19a1cc3a3fc6d72506f6fce2025f738d8b55f29f22125eb0a4",
    3: "04665f660a5052be7a95546a02179058d93d3e08a779734914594346075bb0afd45113948d72cf3dc8f2b70ee02dc1695d051bb0c6da2a914a69045e3277682d3b",
}

privkeys_dev = {
    1: "0x4444444444444444444444444444444444444444444444444444444444444444",
    2: "0x4545454545454545454545454545454545454545454545454545454545454545",
    3: "0xbfc4bca9c9c228a16639d3503d999a733a439210b64cebe757a4fd03ca46a5c8",
}

FWHEADER_SIZE = 1024
SIGNATURES_START = 6 * 4 + 8 + 512
INDEXES_START = SIGNATURES_START + 3 * 64

INDEXES_START_OLD = len("TRZR") + struct.calcsize("<I")
SIG_START = INDEXES_START_OLD + SLOTS + 1 + 52


def parse_args():
    parser = argparse.ArgumentParser(
        description="Commandline tool for signing Trezor firmware."
    )
    parser.add_argument("-f", "--file", dest="path", help="Firmware file to modify")

    return parser.parse_args()


def pad_to_size(data, size):
    if len(data) > size:
        raise ValueError("Chunk too big already")
    if len(data) == size:
        return data
    return data + b"\xFF" * (size - len(data))


# see memory.h for details


def prepare_hashes(data):
    # process chunks
    start = 0
    end = (64 - 1) * 1024
    hashes = []
    for i in range(16):
        sector = data[start:end]
        if len(sector) > 0:
            chunk = pad_to_size(sector, end - start)
            hashes.append(hashlib.sha256(chunk).digest())
        else:
            hashes.append(b"\x00" * 32)
        start = end
        end += 64 * 1024
    return hashes


def check_hashes(data):
    expected_hashes = data[0x20 : 0x20 + 16 * 32]
    hashes = b""
    for h in prepare_hashes(data[FWHEADER_SIZE:]):
        hashes += h

    if expected_hashes == hashes:
        print("HASHES OK")
    else:
        print("HASHES NOT OK")


def update_hashes_in_header(data):
    # Store hashes in the firmware header
    data = bytearray(data)
    o = 0
    for h in prepare_hashes(data[FWHEADER_SIZE:]):
        data[0x20 + o : 0x20 + o + 32] = h
        o += 32
    return bytes(data)


def get_header(data, zero_signatures=False):
    if not zero_signatures:
        return data[:FWHEADER_SIZE]
    else:
        data = bytearray(data[:FWHEADER_SIZE])
        data[SIGNATURES_START : SIGNATURES_START + 3 * 64 + 3] = b"\x00" * (3 * 64 + 3)
        return bytes(data)


def check_size(data):
    size = struct.unpack("<L", data[12:16])[0]
    assert size == len(data) - 1024


def check_signatures(data):
    # Analyses given firmware and prints out
    # status of included signatures

    indexes = [x for x in data[INDEXES_START : INDEXES_START + SLOTS]]

    to_sign = get_header(data, zero_signatures=True)
    fingerprint = hashlib.sha256(to_sign).hexdigest()

    print("Firmware fingerprint:", fingerprint)

    used = []
    for x in range(SLOTS):
        signature = data[SIGNATURES_START + 64 * x : SIGNATURES_START + 64 * x + 64]

        if indexes[x] == 0:
            print(f"Slot #{x + 1}", "is empty")
        else:
            pubkeys = pubkeys_dev
            pk = pubkeys[indexes[x]]
            verify = ecdsa.VerifyingKey.from_string(
                bytes.fromhex(pk)[1:],
                curve=ecdsa.curves.SECP256k1,
                hashfunc=hashlib.sha256,
            )

            try:
                verify.verify(signature, to_sign, hashfunc=hashlib.sha256)

                if indexes[x] in used:
                    print(f"Slot #{x + 1} signature: DUPLICATE", signature.hex())
                else:
                    used.append(indexes[x])
                    print(f"Slot #{x + 1} signature: VALID", signature.hex())

            except Exception:
                print(f"Slot #{x + 1} signature: INVALID", signature.hex())


def modify(data, slot, index, signature):
    data = bytearray(data)
    # put index to data
    data[INDEXES_START + slot - 1] = index
    # put signature to data
    data[SIGNATURES_START + 64 * (slot - 1) : SIGNATURES_START + 64 * slot] = signature
    return bytes(data)


def sign(data, slot, secexp):
    key = ecdsa.SigningKey.from_secret_exponent(
        secexp=int(secexp, 16),
        curve=ecdsa.curves.SECP256k1,
        hashfunc=hashlib.sha256,
    )

    to_sign = get_header(data, zero_signatures=True)

    # Locate proper index of current signing key
    pubkey = "04" + key.get_verifying_key().to_string().hex()
    index = None

    pubkeys = pubkeys_dev
    for i, pk in pubkeys.items():
        if pk == pubkey:
            index = i
            break

    if index is None:
        raise Exception("Unable to find private key index. Unknown private key?")

    signature = key.sign_deterministic(to_sign, hashfunc=hashlib.sha256)

    return modify(data, slot, index, signature)


def prepare_old(data):
    # Takes raw OR signed firmware and clean out metadata structure
    # This produces 'clean' data for signing

    meta = b"TRZR"  # magic
    if data[:4] == b"TRZR":
        meta += data[4 : 4 + struct.calcsize("<I")]
    else:
        meta += struct.pack("<I", len(data))  # length of the code
    meta += b"\x00" * SLOTS  # signature index #1-#3
    meta += b"\x01"  # flags
    meta += b"\x00" * 52  # reserved
    meta += b"\x00" * 64 * SLOTS  # signature #1-#3

    if data[:4] == b"TRZR":
        # Replace existing header
        out = meta + data[len(meta) :]
    else:
        # create data from meta + code
        out = meta + data

    return out


def check_signatures_old(data):
    # Analyses given firmware and prints out
    # status of included signatures

    try:
        indexes = [ord(x) for x in data[INDEXES_START_OLD : INDEXES_START_OLD + SLOTS]]
    except TypeError:
        indexes = [x for x in data[INDEXES_START_OLD : INDEXES_START_OLD + SLOTS]]

    to_sign = prepare_old(data)[256:]  # without meta
    fingerprint = hashlib.sha256(to_sign).hexdigest()

    print("Firmware fingerprint:", fingerprint)

    used = []
    for x in range(SLOTS):
        signature = data[SIG_START + 64 * x : SIG_START + 64 * x + 64]

        if indexes[x] == 0:
            print("Slot #%d" % (x + 1), "is empty")
        else:
            pubkeys = pubkeys_dev
            pk = pubkeys[indexes[x]]
            verify = ecdsa.VerifyingKey.from_string(
                bytes.fromhex(pk)[1:],
                curve=ecdsa.curves.SECP256k1,
                hashfunc=hashlib.sha256,
            )

            try:
                verify.verify(signature, to_sign, hashfunc=hashlib.sha256)

                if indexes[x] in used:
                    print("Slot #%d signature: DUPLICATE" % (x + 1), signature.hex())
                else:
                    used.append(indexes[x])
                    print("Slot #%d signature: VALID" % (x + 1), signature.hex())

            except BadSignatureError:
                print("Slot #%d signature: INVALID" % (x + 1), signature.hex())


def modify_old(data, slot, index, signature):
    # Replace signature in data

    # Put index to data
    data = (
        data[: INDEXES_START_OLD + slot - 1]
        + bytes([index])
        + data[INDEXES_START_OLD + slot :]
    )

    # Put signature to data
    data = (
        data[: SIG_START + 64 * (slot - 1)] + signature + data[SIG_START + 64 * slot :]
    )

    return data


def sign_old(data, slot, secexp):
    key = ecdsa.SigningKey.from_secret_exponent(
        secexp=int(secexp, 16),
        curve=ecdsa.curves.SECP256k1,
        hashfunc=hashlib.sha256,
    )

    to_sign = prepare_old(data)[256:]  # without meta

    # Locate proper index of current signing key
    pubkey = "04" + key.get_verifying_key().to_string().hex()
    index = None

    pubkeys = pubkeys_dev

    for i, pk in pubkeys.items():
        if pk == pubkey:
            index = i
            break

    if index is None:
        raise Exception("Unable to find private key index. Unknown private key?")

    signature = key.sign_deterministic(to_sign, hashfunc=hashlib.sha256)

    return modify_old(data, slot, index, signature)


def main(args):
    if not args.path:
        raise Exception("-f/--file is required")

    data = open(args.path, "rb").read()
    assert len(data) % 4 == 0

    if data[:4] != b"TRZF":
        raise Exception("Firmware header expected")

    data = update_hashes_in_header(data)

    print(f"Firmware size {len(data)} bytes")

    check_size(data)
    check_signatures(data)
    check_hashes(data)

    data = sign(data, 1, privkeys_dev[1])
    data = sign(data, 2, privkeys_dev[2])
    data = sign(data, 3, privkeys_dev[3])
    check_signatures(data)
    check_hashes(data)

    fp = open(args.path, "wb")
    fp.write(data)
    fp.close()

    data = prepare_old(data)
    check_signatures_old(data)
    data = sign_old(data, 1, privkeys_dev[1])
    data = sign_old(data, 2, privkeys_dev[2])
    data = sign_old(data, 3, privkeys_dev[3])
    check_signatures_old(data)

    fp = open(args.path, "wb")
    fp.write(data)
    fp.close()


if __name__ == "__main__":
    args = parse_args()
    main(args)
