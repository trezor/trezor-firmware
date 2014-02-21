import os
import binascii
import hashlib
import unicodedata

import tools
import messages_pb2 as proto
import types_pb2 as types
from trezorlib.debuglink import DebugLink
from mnemonic import Mnemonic

# monkeypatching: text formatting of protobuf messages
tools.monkeypatch_google_protobuf_text_format()

def get_buttonrequest_value(code):
    # Converts integer code to its string representation of ButtonRequestType
    return [ k for k, v in types.ButtonRequestType.items() if v == code][0]

def pprint(msg):
    if isinstance(msg, proto.FirmwareUpload):
        return "<%s> (%d bytes):\n" % (msg.__class__.__name__, msg.ByteSize())
    else:
        return "<%s> (%d bytes):\n%s" % (msg.__class__.__name__, msg.ByteSize(), msg)

class CallException(Exception):
    def __init__(self, code, message):
        super(CallException, self).__init__()
        self.args = [code, message]

class PinException(CallException):
    pass

class field(object):
    # Decorator extracts single value from
    # protobuf object. If the field is not
    # present, raises an exception.
    def __init__(self, field):
        self.field = field

    def __call__(self, f):
        def wrapped_f(*args, **kwargs):
            ret = f(*args, **kwargs)
            ret.HasField(self.field)
            return getattr(ret, self.field)
        return wrapped_f

class expect(object):
    # Decorator checks if the method
    # returned one of expected protobuf messages
    # or raises an exception
    def __init__(self, *expected):
        self.expected = expected
        
    def __call__(self, f):
        def wrapped_f(*args, **kwargs):
            ret = f(*args, **kwargs)
            if not isinstance(ret, self.expected):
                raise Exception("Got %s, expected %s" % (ret.__class__, self.expected))
            return ret
        return wrapped_f

def normalize_nfc(txt):
    # Normalize string to UTF8 NFC for sign_message
    if isinstance(txt, str):
        utxt = txt.decode('utf8')
    elif isinstance(txt, unicode):
        utxt = txt
    else:
        raise Exception("String value expected")

    return unicodedata.normalize('NFC', utxt)

class BaseClient(object):
    # Implements very basic layer of sending raw protobuf
    # messages to device and getting its response back.
    def __init__(self, transport, **kwargs):
        self.transport = transport
        super(BaseClient, self).__init__()  # *args, **kwargs)

    def call_raw(self, msg):
        try:
            self.transport.session_begin()
            self.transport.write(msg)
            resp = self.transport.read_blocking()
        finally:
            self.transport.session_end()

        return resp

    def call(self, msg):
        try:
            self.transport.session_begin()

            resp = self.call_raw(msg)
            handler_name = "callback_%s" % resp.__class__.__name__
            handler = getattr(self, handler_name, None)

            if handler != None:
                msg = handler(resp)
                if msg == None:
                    raise Exception("Callback %s must return protobuf message, not None" % handler)

                resp = self.call(msg)

        finally:
            self.transport.session_end()

        return resp

    def callback_Failure(self, msg):
        if msg.code in (types.Failure_PinInvalid,
            types.Failure_PinCancelled, types.Failure_PinExpected):
            raise PinException(msg.code, msg.message)

        raise CallException(msg.code, msg.message)

    def close(self):
        self.transport.close()

class DebugWireMixin(object):
    def call_raw(self, msg):
        print "SENDING", pprint(msg)
        resp = super(DebugWireMixin, self).call_raw(msg)
        print "RECEIVED", pprint(resp)
        return resp

class TextUIMixin(object):
    # This class demonstrates easy test-based UI
    # integration between the device and wallet.
    # You can implement similar functionality
    # by implementing your own GuiMixin with
    # graphical widgets for every type of these callbacks.

    def __init__(self, *args, **kwargs):
        super(TextUIMixin, self).__init__(*args, **kwargs)

    def callback_ButtonRequest(self, msg):
        print "Sending ButtonAck for %s " % get_buttonrequest_value(msg.code)
        return proto.ButtonAck()

    def callback_PinMatrixRequest(self, msg):
        pin = raw_input("PIN required: %s " % msg.message)
        return proto.PinMatrixAck(pin=pin)

    def callback_PassphraseRequest(self, msg):
        passphrase = raw_input("Passphrase required: ")
        passphrase = str(bytearray(passphrase, 'utf-8'))

        return proto.PassphraseAck(passphrase=passphrase)

    def callback_WordRequest(self, msg):
        word = raw_input("Enter one word of mnemonic: ")
        return proto.WordAck(word=word)

class DebugLinkMixin(object):
    # This class implements automatic responses
    # and other functionality for unit tests
    # for various callbacks, created in order
    # to automatically pass unit tests.
    #
    # This mixing should be used only for purposes
    # of unit testing, because it will fail to work
    # without special DebugLink interface provided
    # by the device.

    def __init__(self, *args, **kwargs):
        super(DebugLinkMixin, self).__init__(*args, **kwargs)
        self.debug = None
        self.in_with_statement = 0

        # Always press Yes and provide correct pin
        self.setup_debuglink(True, True)
        
        # Do not expect any specific response from device
        self.expected_responses = None

        # Use blank passphrase
        self.set_passphrase('')

    def close(self):
        super(DebugLinkMixin, self).close()
        if self.debug:
            self.debug.close()

    def set_debuglink(self, debug_transport):
        self.debug = DebugLink(debug_transport)

    def __enter__(self):
        # For usage in with/expected_responses
        self.in_with_statement += 1
        return self

    def __exit__(self, *args):
        self.in_with_statement -= 1

        # Evaluate missed responses in 'with' statement
        if self.expected_responses != None and len(self.expected_responses):
            raise Exception("Some of expected responses didn't come from device: %s" % \
                    [ pprint(x) for x in self.expected_responses ])

        # Cleanup
        self.expected_responses = None
        return False

    def set_expected_responses(self, expected):
        if not self.in_with_statement:
            raise Exception("Must be called inside 'with' statement")
        self.expected_responses = expected

    def setup_debuglink(self, button, pin_correct):
        self.button = button  # True -> YES button, False -> NO button
        self.pin_correct = pin_correct

    def set_passphrase(self, passphrase):
        self.passphrase = str(bytearray(passphrase, 'utf-8'))

    def call_raw(self, msg):
        resp = super(DebugLinkMixin, self).call_raw(msg)
        self._check_request(resp)
        return resp
        
    def _check_request(self, msg):
        if self.expected_responses != None:
            try:
                expected = self.expected_responses.pop(0)
            except IndexError:
                raise CallException(types.Failure_Other,
                        "Got %s, but no message has been expected" % pprint(msg))

            if msg.__class__ != expected.__class__:
                raise CallException(types.Failure_Other,
                            "Expected %s, got %s" % (pprint(expected), pprint(msg)))

            fields = expected.ListFields()  # only filled (including extensions)
            for field, value in fields:
                if not msg.HasField(field.name) or getattr(msg, field.name) != value:
                    raise CallException(types.Failure_Other,
                            "Expected %s, got %s" % (pprint(expected), pprint(msg)))
            
    def callback_ButtonRequest(self, msg):
        print "ButtonRequest code:", get_buttonrequest_value(msg.code)

        print "Pressing button", self.button
        self.debug.press_button(self.button)
        return proto.ButtonAck()

    def callback_PinMatrixRequest(self, msg):
        if self.pin_correct:
            pin = self.debug.read_pin_encoded()
        else:
            pin = '444222'
        return proto.PinMatrixAck(pin=pin)

    def callback_PassphraseRequest(self, msg):
        print "Provided passphrase: '%s'" % self.passphrase
        return proto.PassphraseAck(passphrase=self.passphrase)

    def callback_WordRequest(self, msg):
        raise Exception("Not implemented yet")

class ProtocolMixin(object):
    PRIME_DERIVATION_FLAG = 0x80000000

    def __init__(self, *args, **kwargs):
        super(ProtocolMixin, self).__init__(*args, **kwargs)
        self.init_device()
        
        def get_tx_func_placeholder(txhash):
            raise Exception("Please call set_tx_func() first.")
        self.get_tx_func = get_tx_func_placeholder

    def set_tx_func(self, tx_func):
        self.get_tx_func = tx_func

    def init_device(self):
        self.features = expect(proto.Features)(self.call)(proto.Initialize())

    def _get_local_entropy(self):
        return os.urandom(32)

    def _convert_prime(self, n):
        # Convert minus signs to uint32 with flag
        return [ int(abs(x) | self.PRIME_DERIVATION_FLAG) if x < 0 else x for x in n ]

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
                x |= self.PRIME_DERIVATION_FLAG

            path.append(x)

        return path

    @field('node')
    @expect(proto.PublicKey)
    def get_public_node(self, coin_name, n):
        n = self._convert_prime(n)
        return self.call(proto.GetPublicKey(address_n=n, coin_name=coin_name))

    @field('address')
    @expect(proto.Address)
    def get_address(self, coin_name, n):
        n = self._convert_prime(n)
        return self.call(proto.GetAddress(address_n=n, coin_name=coin_name))

    @field('entropy')
    @expect(proto.Entropy)
    def get_entropy(self, size):
        return self.call(proto.GetEntropy(size=size))

    @field('message')
    @expect(proto.Success)
    def ping(self, msg, button_protection=False, pin_protection=False, passphrase_protection=False):
        msg = proto.Ping(message=msg,
                         button_protection=button_protection,
                         pin_protection=pin_protection,
                         passphrase_protection=passphrase_protection)
        return self.call(msg)

    def get_device_id(self):
        return self.features.device_id

    @field('message')
    @expect(proto.Success)
    def apply_settings(self, label=None, language=None):
        settings = proto.ApplySettings()
        if label != None:
            settings.label = label
        if language:
            settings.language = language

        out = self.call(settings)
        self.init_device()  # Reload Features
        return out

    @field('message')
    @expect(proto.Success)
    def change_pin(self, remove=False):
        ret = self.call(proto.ChangePin(remove=remove))
        self.init_device()  # Re-read features
        return ret

    @expect(proto.MessageSignature)
    def sign_message(self, coin_name, n, message):
        n = self._convert_prime(n)

        # Convert message to UTF8 NFC (seems to be a bitcoin-qt standard)
        message = normalize_nfc(message)

        # Convert message to ASCII stream
        message = str(bytearray(message, 'utf-8'))

        return self.call(proto.SignMessage(coin_name=coin_name, address_n=n, message=message))

    def verify_message(self, address, signature, message):
        # Convert message to UTF8 NFC (seems to be a bitcoin-qt standard)
        message = normalize_nfc(message)

        # Convert message to ASCII stream
        message = str(bytearray(message, 'utf-8'))

        try:
            resp = self.call(proto.VerifyMessage(address=address, signature=signature, message=message))
        except CallException as e:
            resp = e
        if isinstance(resp, proto.Success):
            return True
        return False

    @field('tx_size')
    @expect(proto.TxSize)
    def estimate_tx_size(self, coin_name, inputs, outputs):
        msg = proto.EstimateTxSize()
        msg.coin_name = coin_name
        msg.inputs_count = len(inputs)
        msg.outputs_count = len(outputs)
        return self.call(msg)

    def _prepare_simple_sign_tx(self, coin_name, inputs, outputs):
        msg = proto.SimpleSignTx()
        msg.coin_name = coin_name
        msg.inputs.extend(inputs)
        msg.outputs.extend(outputs)

        known_hashes = []
        for inp in inputs:
            if inp.prev_hash in known_hashes:
                continue

            tx = msg.transactions.add()
            tx.CopyFrom(self.get_tx_func(binascii.hexlify(inp.prev_hash)))
            known_hashes.append(inp.prev_hash)

        return msg

    @field('serialized_tx')
    @expect(proto.TxRequest)
    def simple_sign_tx(self, coin_name, inputs, outputs):
        # TODO Deserialize tx and check if inputs/outputs fits
        msg = self._prepare_simple_sign_tx(coin_name, inputs, outputs)
        return self.call(msg)

    def sign_tx(self, coin_name, inputs, outputs):
        # Temporary solution, until streaming is implemented in the firmware
        return self.simple_sign_tx(coin_name, inputs, outputs)

    @field('message')
    @expect(proto.Success)
    def wipe_device(self):
        ret = self.call(proto.WipeDevice())
        self.init_device()
        return ret

    @field('message')
    @expect(proto.Success)
    def recovery_device(self, word_count, passphrase_protection, pin_protection, label, language):
        if self.features.initialized:
            raise Exception("Device is initialized already. Call wipe_device() and try again.")

        if word_count not in (12, 18, 24):
            raise Exception("Invalid word count. Use 12/18/24")

        res = self.call(proto.RecoveryDevice(word_count=int(word_count),
                                   passphrase_protection=bool(passphrase_protection),
                                   pin_protection=bool(pin_protection),
                                   label=label,
                                   language=language,
                                   enforce_wordlist=True))

        self.init_device()
        return res

    @field('message')
    @expect(proto.Success)
    def reset_device(self, display_random, strength, passphrase_protection, pin_protection, label, language):
        if self.features.initialized:
            raise Exception("Device is initialized already. Call wipe_device() and try again.")

        # Begin with device reset workflow
        msg = proto.ResetDevice(display_random=display_random,
                                strength=strength,
                                language=language,
                                passphrase_protection=bool(passphrase_protection),
                                pin_protection=bool(pin_protection),
                                label=label)

        resp = self.call(msg)
        if not isinstance(resp, proto.EntropyRequest):
            raise Exception("Invalid response, expected EntropyRequest")

        external_entropy = self._get_local_entropy()
        print "Computer generated entropy:", binascii.hexlify(external_entropy)
        return self.call(proto.EntropyAck(entropy=external_entropy))

    @field('message')
    @expect(proto.Success)
    def load_device_by_mnemonic(self, mnemonic, pin, passphrase_protection, label, language, skip_checksum=False):
        m = Mnemonic('english')
        if not skip_checksum and not m.check(mnemonic):
            raise Exception("Invalid mnemonic checksum")

        # Convert mnemonic to UTF8 NKFD
        mnemonic = Mnemonic.normalize_string(mnemonic)

        # Convert mnemonic to ASCII stream
        mnemonic = str(bytearray(mnemonic, 'utf-8'))

        if self.features.initialized:
            raise Exception("Device is initialized already. Call wipe_device() and try again.")

        resp = self.call(proto.LoadDevice(mnemonic=mnemonic, pin=pin,
                                          passphrase_protection=passphrase_protection,
                                          language=language,
                                          label=label,
                                          skip_checksum=skip_checksum))
        self.init_device()
        return resp

    @field('message')
    @expect(proto.Success)
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
        return resp

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

class TrezorClient(ProtocolMixin, TextUIMixin, BaseClient):
    pass

class TrezorClientDebug(ProtocolMixin, TextUIMixin, DebugWireMixin, BaseClient):
    pass

class TrezorDebugClient(ProtocolMixin, DebugLinkMixin, DebugWireMixin, BaseClient):
    pass

'''
class TrezorClient(object):
    def _pprint(self, msg):
        ser = msg.SerializeToString()
        return "<%s> (%d bytes):\n%s" % (msg.__class__.__name__, len(ser), msg)

    def call(self, msg, expected=None, expected_buttonrequests=None):
        # TODO split this into normal and debug mode
        if self.debug:
            print '----------------------'
            print "Sending", self._pprint(msg)

        try:
            self.transport.session_begin()

            self.transport.write(msg)
            resp = self.transport.read_blocking()

            if isinstance(resp, proto.ButtonRequest):
           _pprint(self, msg):
        ser = msg.SerializeToString()
             if expected_buttonrequests != None:
                    try:
                        exp = expected_buttonrequests.pop(0)
                        if resp.code != exp:
                            raise CallException(types.Failure_Other, "Expected %s, got %s" % \
                                    (self._get_buttonrequest_value(exp),
                                    self._get_buttonrequest_value(resp.code)))
                    except IndexError:
                        raise CallException(types.Failure_Other,
                                            "Got %s, but no ButtonRequest has been expected" % \
                                            self._get_buttonrequest_value(resp.code))

                print "ButtonRequest code:", self._get_buttonrequest_value(resp.code)
                if self.debuglink and self.debug_button:
                    print "Pressing button", self.debug_button
                    self.debuglink.press_button(self.debug_button)

                return self.call(proto.ButtonAck(), expected_buttonrequests=expected_buttonrequests)

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

                return self.call(msg2, expected=expected, expected_buttonrequests=expected_buttonrequests)

            if isinstance(resp, proto.PassphraseRequest):
                passphrase = self.passphrase_func("Passphrase required: ")
                ms(object)g2 = proto.PassphraseAck(passphrase=passphrase)
                return self.call(msg2, expected=expected, expected_buttonrequests=expected_buttonrequests)

        finally:
            self.transport.session_end()

        if isinstance(resp, proto.Failure):
            self.message_func(resp.message)

            if resp.code in (types.Failure_PinInvalid,
                types.Failure_PinCancelled, types.Failure_PinExpected):
                raise PinException(resp.code, resp.message)

            raise CallException(resp.code, resp.message)

        if self.debug:
            print "Received", self._pprint(resp)

        if expected and not isinstance(resp, expected):
            raise CallException("Expected %s message, got %s message" % (expected.DESCRIPTOR.name, resp.DESCRIPTOR.name))

        if expected_buttonrequests != None and len(expected_buttonrequests):
            raise CallException(types.Failure_Other,
                    "Following ButtonRequests were not in use: %s" % \
                    [ self._get_buttonrequest_value(x) for x in expected_buttonrequests])

        return resp

    def _sign_tx(self, coin_name, inputs, outputs):
        ''
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
        ''

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
'''
