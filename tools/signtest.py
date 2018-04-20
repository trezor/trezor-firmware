#!/usr/bin/env python
import binascii
import os
import random
import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types
import trezorlib.tools as tools
import trezorlib.ckd_public as bip32

import hashlib
from trezorlib.client import TrezorClient
from trezorlib.tx_api import TxApiTestnet
from trezorlib.tx_api import TxApiBitcoin
from trezorlib.transport import get_transport


def hash160(x):
    h = hashlib.new("ripemd160")
    h.update(hashlib.sha256(x).digest())
    return h.digest()


def pack_varint(x):
    if (x < 0xfd):
        return chr(x)
    else:
        return '\xfd' + chr(x & 0xff) + chr((x >> 8) & 0xff)


def int_to_string(x, pad):
    result = ['\x00'] * pad
    while x > 0:
        pad -= 1
        ordinal = x & 0xFF
        result[pad] = (chr(ordinal))
        x >>= 8
    return ''.join(result)


def string_to_int(s):
    result = 0
    for c in s:
        if not isinstance(c, int):
            c = ord(c)
        result = (result << 8) + c
    return result


class MyTxApiBitcoin(object):

    def set_publickey(self, node):
        self.node = node.node

    def set_client(self, client):
        self.client = client

    def serialize_tx(self, tx):
        ser = ''
        ser = ser + int_to_string(tx.version, 4)[::-1]
        ser = ser + pack_varint(len(tx.inputs))
        for i in tx.inputs:
            ser = ser + i.prev_hash[::-1]
            ser = ser + int_to_string(i.prev_index, 4)[::-1]
            ser = ser + pack_varint(len(i.script_sig)) + i.script_sig
            ser = ser + int_to_string(i.sequence, 4)[::-1]
        ser = ser + pack_varint(len(tx.bin_outputs))
        for o in tx.bin_outputs:
            ser = ser + int_to_string(o.amount, 8)[::-1]
            ser = ser + pack_varint(len(o.script_pubkey)) + o.script_pubkey
        ser = ser + int_to_string(tx.lock_time, 4)[::-1]
        return ser

    def create_inputs(self, numinputs, txsize):
        idx = 0
        sum = 0
        self.inputs = []
        self.txs = {}
        for nr in range(numinputs):
            t = proto_types.TransactionType()
            t.version = 1
            t.lock_time = 0
            i = t.inputs.add()
            i.prev_hash = os.urandom(32)
            i.prev_index = random.randint(0, 4)
            i.script_sig = os.urandom(100)
            i.sequence = 0xffffffff
            if nr % 50 == 0:
                print(nr)
            myout = random.randint(0, txsize - 1)
            segwit = random.randint(0, 2)
            for vout in range(txsize):
                o = t.bin_outputs.add()
                o.amount = random.randint(10000, 1000000)
                if vout == myout:
                    amount = o.amount
                    sum = sum + o.amount
                    node = self.node
                    path = [0, idx]
                    node = bip32.public_ckd(node, path)
                    idx = idx + 1
                    pubkey = tools.hash_160(node.public_key)
                else:
                    pubkey = os.urandom(20)
                if segwit == 2:
                    # p2sh segwit
                    o.script_pubkey = b'\xa9\x14' + hash160(b'\x00\x14' + pubkey) + b'\x87'
                elif segwit == 1:
                    o.script_pubkey = b'\x00\x14' + pubkey
                else:
                    o.script_pubkey = b'\x76\xa9\x14' + pubkey + b'\x88\xac'

            txser = self.serialize_tx(t)
            txhash = tools.btc_hash(txser)[::-1]
            self.inputs.append(
                proto_types.TxInputType(
                    address_n=self.client.expand_path("44'/0'/0'/0/%d" % idx),
                    script_type=(
                        proto_types.SPENDWITNESS if segwit == 1 else
                        proto_types.SPENDP2SHWITNESS if segwit == 2 else
                        proto_types.SPENDADDRESS
                    ),
                    prev_hash=txhash,
                    prev_index=myout,
                    amount=amount if segwit > 0 else 0
                ))
            # print(binascii.hexlify(txser))
            # print(binascii.hexlify(txhash))
            self.txs[binascii.hexlify(txhash)] = t

        self.outputs = [
            proto_types.TxOutputType(
                amount=sum,
                script_type=proto_types.PAYTOADDRESS,
                address_n=self.client.expand_path("44'/0'/0'/1/0")
            )]

    def get_inputs(self):
        return self.inputs

    def get_outputs(self):
        return self.outputs

    def get_tx(self, txhash):
        t = self.txs[txhash]
        # print(t)
        return t


def main():
    numinputs = 100
    sizeinputtx = 10

    # Use first connected device
    try:
        transport = get_transport()
    except Exception as e:
        print(e)
        return

    print(transport)

    txstore = MyTxApiBitcoin()

    # Creates object for manipulating TREZOR
    client = TrezorClient(transport)
    # client.set_tx_api(TxApiTestnet)
    txstore.set_client(client)
    txstore.set_publickey(client.get_public_node(client.expand_path("44'/0'/0'")))
    print("creating input txs")
    txstore.create_inputs(numinputs, sizeinputtx)
    print("go")
    client.set_tx_api(txstore)
    # client.set_tx_api(MyTxApiBitcoin())

    # Print out TREZOR's features and settings
    print(client.features)

    # Get the first address of first BIP44 account
    # (should be the same address as shown in wallet.trezor.io)

    # outputs = [
    #     proto_types.TxOutputType(
    #         amount=0,
    #         script_type=proto_types.PAYTOADDRESS,
    #         address='p2xtZoXeX5X8BP8JfFhQK2nD3emtjch7UeFm'
    #         # op_return_data=binascii.unhexlify('2890770995194662774cd192ee383b805e9a066e6a456be037727649228fb7f6')
    #         # address_n=client.expand_path("44'/0'/0'/0/35"),
    #         # address='3PUxV6Cc4udQZQsJhArVUzvvVoKC8ohkAj',
    #     ),
    #     proto_types.TxOutputType(
    #         amount=0,
    #         script_type=proto_types.PAYTOOPRETURN,
    #         op_return_data=binascii.unhexlify('2890770995194662774cd192ee383b805e9a066e6a456be037727649228fb7f6')
    #     ),
    #     proto_types.TxOutputType(
    #         amount= 8120,
    #         script_type=proto_types.PAYTOADDRESS,
    #         address_n=client.expand_path("44'/1'/0'/1/0"),
    #         address='1PtCkQgyN6xHmXWzLmFFrDNA5vYhYLeNFZ',
    #         address='14KRxYgFc7Se8j7MDdrK5PTNv8meq4GivK',
    #     ),
    #     proto_types.TxOutputType(
    #     amount= 18684 - 2000,
    #     script_type=proto_types.PAYTOADDRESS,
    #     address_n=client.expand_path("44'/0'/0'/0/7"),
    #     # address='1PtCkQgyN6xHmXWzLmFFrDNA5vYhYLeNFZ',
    #     # address='1s9TSqr3PHZdXGrYws59Uaf5SPqavH43z',
    #     ),
    #     proto_types.TxOutputType(
    #     amount= 1000,
    #     script_type=proto_types.PAYTOADDRESS,
    #     # address_n=client.expand_path("44'/0'/0'/0/18"),
    #     # address='1PtCkQgyN6xHmXWzLmFFrDNA5vYhYLeNFZ',
    #     # address='1NcMqUvyWv1K3Zxwmx5sqfj7ZEmPCSdJFM',
    #     ),
    # ]

#    (signatures, serialized_tx) = client.sign_tx('Testnet', inputs, outputs)
    (signatures, serialized_tx) = client.sign_tx('Bitcoin', txstore.get_inputs(), txstore.get_outputs())
    print('Transaction:', binascii.hexlify(serialized_tx))

    client.close()


if __name__ == '__main__':
    main()
