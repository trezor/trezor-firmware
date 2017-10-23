#!/usr/bin/python
import subprocess
import os
import json
import time
import ecdsa
import hashlib
import binascii
from google.protobuf.descriptor_pb2 import FileDescriptorSet

PROTOBUF_PROTO_DIR=os.environ.get('PROTOBUF_PROTO_DIR', '/usr/include/')
TREZOR_PROTO_DIR=os.environ.get('TREZOR_PROTO_DIR', '../protob/')

def compile_config():
    cmd = "protoc --python_out=../signer/ -I" + PROTOBUF_PROTO_DIR + " -I./ config.proto"
    subprocess.check_call(cmd.split(), cwd=TREZOR_PROTO_DIR)

def parse_json():
    return json.loads(open('config.json', 'r').read())


def get_compiled_proto():
    # Compile trezor.proto to binary format
    pdir = os.path.abspath(TREZOR_PROTO_DIR)
    pfile = os.path.join(pdir, "messages.proto")
    cmd = "protoc --include_imports -I" + PROTOBUF_PROTO_DIR + " -I" + pdir  + " " + pfile + " -otrezor.bin"

    subprocess.check_call(cmd.split())

    # Load compiled protocol description to string
    proto = open('trezor.bin', 'r').read()
    os.unlink('trezor.bin')

    # Parse it into FileDescriptorSet structure
    compiled = FileDescriptorSet()
    compiled.ParseFromString(proto)
    return compiled

def compose_message(json, proto):
    import config_pb2

    cfg = config_pb2.Configuration()
    cfg.valid_until = 2147483647 # maxint
    cfg.wire_protocol.MergeFrom(proto)

    for url in json['whitelist_urls']:
        cfg.whitelist_urls.append(str(url))

    for url in json['blacklist_urls']:
        cfg.blacklist_urls.append(str(url))

    for dev in json['known_devices']:
        desc = cfg.known_devices.add()
        desc.vendor_id = int(dev[0], 16)
        desc.product_id = int(dev[1], 16)

    return cfg.SerializeToString()

def sign_message(data, key):
    if key.startswith('-----BEGIN'):
        key = ecdsa.keys.SigningKey.from_pem(key)
    else:
        key = ecdsa.keys.SigningKey.from_secret_exponent(secexp = int(key, 16), curve=ecdsa.curves.SECP256k1, hashfunc=hashlib.sha256)

    verify = key.get_verifying_key()
    print "Verifying key:"
    print verify.to_pem()

    return key.sign_deterministic(data, hashfunc=hashlib.sha256)

def pack_datafile(filename, signature, data):
    if len(signature) != 64:
        raise Exception("Signature must be 64 bytes long")

    fp = open(filename, 'w')
    fp.write(binascii.hexlify(signature))
    fp.write(binascii.hexlify(data))
    fp.close()

    print "Signature and data stored to", filename

if __name__ == '__main__':
    key = ''
    print "Paste ECDSA private key (in PEM format or SECEXP format) and press Enter:"
    while True:
        inp = raw_input()
        if inp == '':
            break

        key += inp + "\n"

    # key = open('sample.key', 'r').read()

    compile_config()
    json = parse_json()
    proto = get_compiled_proto()

    data = compose_message(json, proto)
    signature = sign_message(data, key)

    pack_datafile('config_signed.bin', signature, data)
