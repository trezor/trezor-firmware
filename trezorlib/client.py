import os
import time
import binascii
import hashlib

import ckd_public
import tools
import messages_pb2 as proto
import types_pb2 as types
from api_blockchain import BlockchainApi

# monkeypatching: text formatting of protobuf messages
tools.monkeypatch_google_protobuf_text_format()

def show_message(message):
    print "MESSAGE FROM DEVICE:", message

def show_input(input_text, message=None):
    if message:
        print "QUESTION FROM DEVICE:", message
    return raw_input(input_text)

def pin_func(input_text, message=None):
    return show_input(input_text, message)

def passphrase_func(input_text):
    return show_input(input_text)

class CallException(Exception):
    pass

class PinException(CallException):
    pass

PRIME_DERIVATION_FLAG = 0x80000000

class TrezorClient(object):

    def __init__(self, transport, debuglink=None,
                 message_func=show_message, input_func=show_input,
                 pin_func=pin_func, passphrase_func=passphrase_func,
                 blockchain_api=None, debug=False):
        self.transport = transport
        self.debuglink = debuglink

        self.message_func = message_func
        self.input_func = input_func
        self.pin_func = pin_func
        self.passphrase_func = passphrase_func

        self.debug = debug

        if blockchain_api:
            self.blockchain = blockchain_api
        else:
            self.blockchain = BlockchainApi()

        self.setup_debuglink()
        self.init_device()

    def _get_local_entropy(self):
        return os.urandom(32)

    def _convert_prime(self, n):
        # Convert minus signs to uint32 with flag
        return [ int(abs(x) | PRIME_DERIVATION_FLAG) if x < 0 else x for x in n ]

    def expand_path(self, n):
        # Convert string of bip32 path to list of uint32 integers with prime flags
        # 0/-1/1' -> [0, 0x80000001, 0x80000001]
        if not n:
            return []

        n = n.split('/')
        path = []
        for x in n:
            prime = False
            if x.endswith("'"):
                x = x.replace('\'', '')
                prime = True
            if x.startswith('-'):
                prime = True

            x = abs(int(x))

            if prime:
                x |= PRIME_DERIVATION_FLAG

            path.append(x)

        return path

    def init_device(self):
        self.features = self.call(proto.Initialize(), proto.Features)

    def close(self):
        self.transport.close()
        if self.debuglink:
            self.debuglink.transport.close()

    def get_public_node(self, n):
        return self.call(proto.GetPublicKey(address_n=n), proto.PublicKey).node

    def get_address(self, coin_name, n):
        n = self._convert_prime(n)
        return self.call(proto.GetAddress(address_n=n, coin_name=coin_name), proto.Address).address

    def get_entropy(self, size):
        return self.call(proto.GetEntropy(size=size), proto.Entropy).entropy

    def ping(self, msg):
        return self.call(proto.Ping(message=msg), proto.Success).message

    def get_device_id(self):
        return self.features.device_id

    def apply_settings(self, label=None, language=None):
        settings = proto.ApplySettings()
        if label != None:
            settings.label = label
        if language:
            settings.language = language

        out = self.call(settings, proto.Success).message
        self.init_device() # Reload Features

        return out

    def change_pin(self, remove=False):
        ret = self.call(proto.ChangePin(remove=remove))
        self.init_device()  # Re-read features
        return ret

    def _pprint(self, msg):
        return "<%s>:\n%s" % (msg.__class__.__name__, msg)

    def setup_debuglink(self, button=None, pin_correct=False):
        self.debug_button = button
        self.debug_pin = pin_correct

    def call(self, msg, expected = None):
        if self.debug:
            print '----------------------'
            print "Sending", self._pprint(msg)

        try:
            self.transport.session_begin()

            self.transport.write(msg)
            resp = self.transport.read_blocking()

            if isinstance(resp, proto.ButtonRequest):
                if self.debuglink and self.debug_button:
                    print "Pressing button", self.debug_button
                    self.debuglink.press_button(self.debug_button)

                return self.call(proto.ButtonAck())

            if isinstance(resp, proto.PinMatrixRequest):
                if self.debuglink:
                    if self.debug_pin == 1:
                        pin = self.debuglink.read_pin_encoded()
                        msg2 = proto.PinMatrixAck(pin=pin)
                    elif self.debug_pin == -1:
                        msg2 = proto.Cancel()
                    else:
                        msg2 = proto.PinMatrixAck(pin='444444222222')

                else:
                    pin = self.pin_func("PIN required: ", resp.message)
                    msg2 = proto.PinMatrixAck(pin=pin)

                return self.call(msg2)

            if isinstance(resp, proto.PassphraseRequest):
                passphrase = self.passphrase_func("Passphrase required: ")
                msg2 = proto.PassphraseAck(passphrase=passphrase)
                return self.call(msg2)

        finally:
            self.transport.session_end()

        if isinstance(resp, proto.Failure):
            self.message_func(resp.message)

            if resp.code == types.Failure_ActionCancelled:
                raise CallException("Action cancelled by user")

            elif resp.code in (types.Failure_PinInvalid,
                types.Failure_PinCancelled, types.Failure_PinExpected):
                raise PinException("PIN is invalid")

            raise CallException(resp.code, resp.message)

        if self.debug:
            print "Received", self._pprint(resp)

        if expected and not isinstance(resp, expected):
            raise CallException("Expected %s message, got %s message" % (expected.DESCRIPTOR.name, resp.DESCRIPTOR.name))

        return resp

    def sign_message(self, n, message):
        n = self._convert_prime(n)
        return self.call(proto.SignMessage(address_n=n, message=message))

    def verify_message(self, address, signature, message):
        try:
            resp = self.call(proto.VerifyMessage(address=address, signature=signature, message=message))
            if isinstance(resp, proto.Success):
                return True
        except CallException:
            pass

        return False

    def estimate_tx_size(self, coin_name, inputs, outputs):
        msg = proto.EstimateTxSize()
        msg.coin_name = coin_name
        msg.inputs_count = len(inputs)
        msg.outputs_count = len(outputs)
        res = self.call(msg)
        return res.tx_size

    def simple_sign_tx(self, coin_name, inputs, outputs):
        msg = proto.SimpleSignTx()
        msg.coin_name = coin_name
        msg.inputs.extend(inputs)
        msg.outputs.extend(outputs)

        known_hashes = []
        for inp in inputs:
            if inp.prev_hash in known_hashes:
                continue

            tx = msg.transactions.add()
            tx.CopyFrom(self.blockchain.get_tx(binascii.hexlify(inp.prev_hash)))
            known_hashes.append(inp.prev_hash)

        return self.call(msg)

    def sign_tx(self, coin_name, inputs, outputs):
        # Temporary solution, until streaming is implemented in the firmware
        return self.simple_sign_tx(coin_name, inputs, outputs)

    def _sign_tx(self, coin_name, inputs, outputs):
        '''
            inputs: list of TxInput
            outputs: list of TxOutput

            proto.TxInput(index=0,
                          address_n=0,
                          amount=0,
                          prev_hash='',
                          prev_index=0,
                          #script_sig=
                          )
            proto.TxOutput(index=0,
                          address='1Bitkey',
                          #address_n=[],
                          amount=100000000,
                          script_type=proto.PAYTOADDRESS,
                          #script_args=
                          )
        '''

        start = time.time()

        try:
            self.transport.session_begin()

            # Prepare and send initial message
            tx = proto.SignTx()
            tx.inputs_count = len(inputs)
            tx.outputs_count = len(outputs)
            res = self.call(tx)

            # Prepare structure for signatures
            signatures = [None]*len(inputs)
            serialized_tx = ''

            counter = 0
            while True:
                counter += 1

                if isinstance(res, proto.Failure):
                    raise CallException("Signing failed")

                if not isinstance(res, proto.TxRequest):
                    raise CallException("Unexpected message")

                # If there's some part of signed transaction, let's add it
                if res.serialized_tx:
                    print "!!! RECEIVED PART OF SERIALIED TX (%d BYTES)" % len(res.serialized_tx)
                    serialized_tx += res.serialized_tx

                if res.signed_index >= 0 and res.signature:
                    print "!!! SIGNED INPUT", res.signed_index
                    signatures[res.signed_index] = res.signature

                if res.request_index < 0:
                    # Device didn't ask for more information, finish workflow
                    break

                # Device asked for one more information, let's process it.
                if res.request_type == types.TXOUTPUT:
                    res = self.call(outputs[res.request_index])
                    continue

                elif res.request_type == types.TXINPUT:
                    print "REQUESTING", res.request_index
                    res = self.call(inputs[res.request_index])
                    continue

        finally:
            self.transport.session_end()

        print "SIGNED IN %.03f SECONDS, CALLED %d MESSAGES, %d BYTES" % \
                (time.time() - start, counter, len(serialized_tx))

        return (signatures, serialized_tx)

    def wipe_device(self):
        ret = self.call(proto.WipeDevice())
        self.init_device()
        return ret

    def reset_device(self, display_random, strength, passphrase_protection, pin_protection, label, language):
        if self.features.initialized:
            raise Exception("Device is initialized already. Call wipe_device() and try again.")

        # Begin with device reset workflow
        msg = proto.ResetDevice(display_random=display_random,
                                           strength=strength,
                                           language=language,
                                           passphrase_protection=bool(passphrase_protection),
                                           pin_protection=bool(pin_protection),
                                           label=label
                                           )
        resp = self.call(msg)
        if not isinstance(resp, proto.EntropyRequest):
            raise Exception("Invalid response, expected EntropyRequest")

        external_entropy = self._get_local_entropy()
        print "Computer generated entropy:", binascii.hexlify(external_entropy)
        resp = self.call(proto.EntropyAck(entropy=external_entropy))


        return isinstance(resp, proto.Success)

    def load_device_by_mnemonic(self, mnemonic, pin, passphrase_protection, label, language):
        if self.features.initialized:
            raise Exception("Device is initialized already. Call wipe_device() and try again.")

        resp = self.call(proto.LoadDevice(mnemonic=mnemonic, pin=pin,
                                          passphrase_protection=passphrase_protection,
                                          language=language,
                                          label=label))
        self.init_device()
        return isinstance(resp, proto.Success)

    def load_device_by_xprv(self, xprv, pin, passphrase_protection, label):
        if self.features.initialized:
            raise Exception("Device is initialized already. Call wipe_device() and try again.")

        if xprv[0:4] not in ('xprv', 'tprv'):
            raise Exception("Unknown type of xprv")

        if len(xprv) < 100 and len(xprv) > 112:
            raise Exception("Invalid length of xprv")

        node = types.HDNodeType()
        data = tools.b58decode(xprv, None).encode('hex')

        if data[90:92] != '00':
            raise Exception("Contain invalid private key")

        checksum = hashlib.sha256(hashlib.sha256(binascii.unhexlify(data[:156])).digest()).hexdigest()[:8]
        if checksum != data[156:]:
            raise Exception("Checksum doesn't match")

        # version 0488ade4
        # depth 00
        # fingerprint 00000000
        # child_num 00000000
        # chaincode 873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508
        # privkey   00e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35
        # checksum e77e9d71

        node.version = int(data[0:8], 16)
        node.depth = int(data[8:10], 16)
        node.fingerprint = int(data[10:18], 16)
        node.child_num = int(data[18:26], 16)
        node.chain_code = data[26:90].decode('hex')
        node.private_key = data[92:156].decode('hex')  # skip 0x00 indicating privkey

        resp = self.call(proto.LoadDevice(node=node,
                                          pin=pin,
                                          passphrase_protection=passphrase_protection,
                                          language='english',
                                          label=label))
        self.init_device()
        return isinstance(resp, proto.Success)

    def firmware_update(self, fp):
        if self.features.bootloader_mode == False:
            raise Exception("Device must be in bootloader mode")

        resp = self.call(proto.FirmwareErase())
        if isinstance(resp, proto.Failure) and resp.code == types.Failure_FirmwareError:
            return False

        resp = self.call(proto.FirmwareUpload(payload=fp.read()))
        if isinstance(resp, proto.Success):
            return True

        elif isinstance(resp, proto.Failure) and resp.code == types.Failure_FirmwareError:
            return False

        raise Exception("Unexpected result " % resp)
