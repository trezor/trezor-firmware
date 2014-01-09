import os
import time
import binascii
import hashlib

import ckd_public
import tools
import messages_pb2 as proto
import types_pb2 as types

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
                 message_func=show_message, input_func=show_input, pin_func=pin_func, passphrase_func=passphrase_func, debug=False):
        self.transport = transport
        self.debuglink = debuglink
        
        self.message_func = message_func
        self.input_func = input_func
        self.pin_func = pin_func
        self.passphrase_func = passphrase_func
        self.debug = debug
        
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
        n = n.split('/')
        path = []
        for x in n:
            prime = False
            if '\'' in x:
                x = x.replace('\'', '')
                prime = True
            if '-' in x:
                prime = True
                
            if prime:
                path.append(abs(int(x)) | PRIME_DERIVATION_FLAG)
            else:
                path.append(abs(int(x)))

        return path

    def init_device(self):
        self.features = self.call(proto.Initialize())

    def close(self):
        self.transport.close()
        if self.debuglink:
            self.debuglink.transport.close()

    def get_public_node(self, n):
        return self.call(proto.GetPublicKey(address_n=n)).node
        
    def get_address(self, coin_name, n):
        return self.call(proto.GetAddress(address_n=n, coin_name=coin_name)).address
        
    def get_entropy(self, size):
        return self.call(proto.GetEntropy(size=size)).entropy

    def ping(self, msg):
        return self.call(proto.Ping(message=msg)).message

    def get_device_id(self):
        return self.features.device_id

    def apply_settings(self, label=None, coin_shortcut=None, language=None):
        settings = proto.ApplySettings()
        if label:
            settings.label = label
        if coin_shortcut:
            settings.coin_shortcut = coin_shortcut
        if language:
            settings.language = language

        out = self.call(settings).message
        self.init_device() # Reload Features

        return out

    def _pprint(self, msg):
        return "<%s>:\n%s" % (msg.__class__.__name__, msg)

    def setup_debuglink(self, button=None, pin_correct=False):
        self.debug_button = button
        self.debug_pin = pin_correct
        
    def call(self, msg):
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
                
            elif resp.code == types.Failure_PinInvalid:
                raise PinException("PIN is invalid")
                
            raise CallException(resp.code, resp.message)
        
        if self.debug:
            print "Received", self._pprint(resp)
            
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

    def sign_tx(self, inputs, outputs):
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
                
        #print "PBDATA", tx.SerializeToString().encode('hex')
        
        #################
        #################
        #################
        
        '''
        signatures = [('add550d6ba9ab7e01d37e17658f98b6e901208d241f24b08197b5e20dfa7f29f095ae01acbfa5c4281704a64053dcb80e9b089ecbe09f5871d67725803e36edd', '3045022100dced96eeb43836bc95676879eac303eabf39802e513f4379a517475c259da12502201fd36c90ecd91a32b2ca8fed2e1755a7f2a89c2d520eb0da10147802bc7ca217')]
        
        s_inputs = []
        for i in range(len(inputs)):
            addr, v, p_hash, p_pos, p_scriptPubKey, _, _ = inputs[i]
            pubkey = signatures[i][0].decode('hex')
            sig = signatures[i][1].decode('hex')
            s_inputs.append((addr, v, p_hash, p_pos, p_scriptPubKey, pubkey, sig))
        
        return s_inputs
                
        s_inputs = []
        for i in range(len(inputs)):
            addr, v, p_hash, p_pos, p_scriptPubKey, _, _ = inputs[i]
            private_key = ecdsa.SigningKey.from_string( self.get_private_key(addr, password), curve = SECP256k1 )
            public_key = private_key.get_verifying_key()
            pubkey = public_key.to_string()
            tx = filter( raw_tx( inputs, outputs, for_sig = i ) )
            sig = private_key.sign_digest( Hash( tx.decode('hex') ), sigencode = ecdsa.util.sigencode_der )
            assert public_key.verify_digest( sig, Hash( tx.decode('hex') ), sigdecode = ecdsa.util.sigdecode_der)
            s_inputs.append( (addr, v, p_hash, p_pos, p_scriptPubKey, pubkey, sig) )
        return s_inputs
        '''

    def reset_device(self, display_random, strength, passphrase_protection, pin_protection, label):
        # Begin with device reset workflow
        msg = proto.ResetDevice(display_random=display_random,
                                           strength=strength,
                                           language='english',
                                           passphrase_protection=bool(passphrase_protection),
                                           pin_protection=bool(pin_protection),
                                           label=label
                                           )
        print msg
        resp = self.call(msg)
        if not isinstance(resp, proto.EntropyRequest):
            raise Exception("Invalid response, expected EntropyRequest")

        external_entropy = self._get_local_entropy()
        print "Computer generated entropy:", binascii.hexlify(external_entropy)
        resp = self.call(proto.EntropyAck(entropy=external_entropy))


        return isinstance(resp, proto.Success)
    
    def load_device_by_mnemonic(self, mnemonic, pin, passphrase_protection, label):
        resp = self.call(proto.LoadDevice(mnemonic=mnemonic, pin=pin,
                                          passphrase_protection=passphrase_protection,
                                          language='english',
                                          label=label))
        self.init_device()
        return isinstance(resp, proto.Success)

    def load_device_by_xprv(self, xprv, pin, passphrase_protection, label):
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

    def bip32_ckd(self, public_node, n):
        if not isinstance(n, list):
            raise Exception('Parameter must be a list')

        node = types.HDNodeType()
        node.CopyFrom(public_node)

        for i in n:
            node.CopyFrom(ckd_public.get_subnode(node, i))

        return node

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
