#!/usr/bin/env python3
from __future__ import print_function

import argparse
import hashlib
import struct

import ecdsa

try:
    raw_input
except:
    raw_input = input

SLOTS = 3

pubkeys = {
    1: "04d571b7f148c5e4232c3814f777d8faeaf1a84216c78d569b71041ffc768a5b2d810fc3bb134dd026b57e65005275aedef43e155f48fc11a32ec790a93312bd58",
    2: "0463279c0c0866e50c05c799d32bd6bab0188b6de06536d1109d2ed9ce76cb335c490e55aee10cc901215132e853097d5432eda06b792073bd7740c94ce4516cb1",
    3: "0443aedbb6f7e71c563f8ed2ef64ec9981482519e7ef4f4aa98b27854e8c49126d4956d300ab45fdc34cd26bc8710de0a31dbdf6de7435fd0b492be70ac75fde58",
    4: "04877c39fd7c62237e038235e9c075dab261630f78eeb8edb92487159fffedfdf6046c6f8b881fa407c4a4ce6c28de0b19c1f4e29f1fcbc5a58ffd1432a3e0938a",
    5: "047384c51ae81add0a523adbb186c91b906ffb64c2c765802bf26dbd13bdf12c319e80c2213a136c8ee03d7874fd22b70d68e7dee469decfbbb510ee9a460cda45",
}

INDEXES_START = len("TRZR") + struct.calcsize("<I")
SIG_START = INDEXES_START + SLOTS + 1 + 52


def parse_args():
    parser = argparse.ArgumentParser(
        description="Commandline tool for signing Trezor firmware."
    )
    parser.add_argument("-f", "--file", dest="path", help="Firmware file to modify")
    parser.add_argument(
        "-s",
        "--sign",
        dest="sign",
        action="store_true",
        help="Add signature to firmware slot",
    )
    parser.add_argument(
        "-p", "--pem", dest="pem", action="store_true", help="Use PEM instead of SECEXP"
    )
    parser.add_argument(
        "-g",
        "--generate",
        dest="generate",
        action="store_true",
        help="Generate new ECDSA keypair",
    )

    return parser.parse_args()


def prepare(data):
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


def check_signatures(data):
    # Analyses given firmware and prints out
    # status of included signatures

    try:
        indexes = [ord(x) for x in data[INDEXES_START : INDEXES_START + SLOTS]]
    except:
        indexes = [x for x in data[INDEXES_START : INDEXES_START + SLOTS]]

    to_sign = prepare(data)[256:]  # without meta
    fingerprint = hashlib.sha256(to_sign).hexdigest()

    print("Firmware fingerprint:", fingerprint)

    used = []
    for x in range(SLOTS):
        signature = data[SIG_START + 64 * x : SIG_START + 64 * x + 64]

        if indexes[x] == 0:
            print("Slot #%d" % (x + 1), "is empty")
        else:
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

            except:
                print("Slot #%d signature: INVALID" % (x + 1), signature.hex())


def modify(data, slot, index, signature):
    # Replace signature in data

    # Put index to data
    data = (
        data[: INDEXES_START + slot - 1] + bytes([index]) + data[INDEXES_START + slot :]
    )

    # Put signature to data
    data = (
        data[: SIG_START + 64 * (slot - 1)] + signature + data[SIG_START + 64 * slot :]
    )

    return data


def sign(data, is_pem):
    # Ask for index and private key and signs the firmware

    slot = int(raw_input("Enter signature slot (1-%d): " % SLOTS))
    if slot < 1 or slot > SLOTS:
        raise Exception("Invalid slot")

    if is_pem:
        print("Paste ECDSA private key in PEM format and press Enter:")
        print("(blank private key removes the signature on given index)")
        pem_key = ""
        while True:
            key = raw_input()
            pem_key += key + "\n"
            if key == "":
                break
        if pem_key.strip() == "":
            # Blank key,let's remove existing signature from slot
            return modify(data, slot, 0, "\x00" * 64)
        key = ecdsa.SigningKey.from_pem(pem_key)
    else:
        print("Paste SECEXP (in hex) and press Enter:")
        print("(blank private key removes the signature on given index)")
        secexp = raw_input()
        if secexp.strip() == "":
            # Blank key,let's remove existing signature from slot
            return modify(data, slot, 0, "\x00" * 64)
        key = ecdsa.SigningKey.from_secret_exponent(
            secexp=int(secexp, 16),
            curve=ecdsa.curves.SECP256k1,
            hashfunc=hashlib.sha256,
        )

    to_sign = prepare(data)[256:]  # without meta

    # Locate proper index of current signing key
    pubkey = "04" + key.get_verifying_key().to_string().hex()
    index = None
    for i, pk in pubkeys.items():
        if pk == pubkey:
            index = i
            break

    if index == None:
        raise Exception("Unable to find private key index. Unknown private key?")

    signature = key.sign_deterministic(to_sign, hashfunc=hashlib.sha256)

    return modify(data, slot, index, signature)


def main(args):
    if args.generate:
        key = ecdsa.SigningKey.generate(
            curve=ecdsa.curves.SECP256k1, hashfunc=hashlib.sha256
        )

        print("PRIVATE KEY (SECEXP):")
        print(key.to_string().hex())
        print()

        print("PRIVATE KEY (PEM):")
        print(key.to_pem())

        print("PUBLIC KEY:")
        print("04" + key.get_verifying_key().to_string().hex())
        return

    if not args.path:
        raise Exception("-f/--file is required")

    data = open(args.path, "rb").read()
    assert len(data) % 4 == 0

    if data[:4] != b"TRZR":
        print("Metadata has been added...")
        data = prepare(data)

    if data[:4] != b"TRZR":
        raise Exception("Firmware header expected")

    print("Firmware size %d bytes" % len(data))

    check_signatures(data)

    if args.sign:
        data = sign(data, args.pem)
        check_signatures(data)

    fp = open(args.path, "wb")
    fp.write(data)
    fp.close()


if __name__ == "__main__":
    args = parse_args()
    main(args)
