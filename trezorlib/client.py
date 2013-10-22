import os
import time

import trezor_pb2 as proto

def show_message(message):
    print "MESSAGE FROM DEVICE:", message
    
def show_input(input_text, message=None):
    if message:
        print "QUESTION FROM DEVICE:", message
    return raw_input(input_text)

def pin_func(input_text, message=None):
    return show_input(input_text, message)

class CallException(Exception):
    pass

class PinException(CallException):
    pass

class TrezorClient(object):
    
    def __init__(self, transport, debuglink=None, 
                 message_func=show_message, input_func=show_input, pin_func=pin_func, debug=False):
        self.transport = transport
        self.debuglink = debuglink
        
        self.message_func = message_func
        self.input_func = input_func
        self.pin_func = pin_func
        self.debug = debug
        
        self.setup_debuglink()
        self.init_device()
    
    def _get_local_entropy(self):
        return os.urandom(32)
        
    def init_device(self):
        self.master_public_key = None
        self.features = self.call(proto.Initialize())

    def close(self):
        self.transport.close()
        if self.debuglink:
            self.debuglink.transport.close()

    def get_master_public_key(self):
        if self.master_public_key:
            return self.master_public_key
        
        self.master_public_key = self.call(proto.GetMasterPublicKey()).mpk
        return self.master_public_key
        
    def get_address(self, n):
        return self.call(proto.GetAddress(address_n=n)).address
        
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
                        msg2 = proto.PinMatrixCancel()
                    else:
                        msg2 = proto.PinMatrixAck(pin='444444222222')

                else:
                    pin = self.pin_func("PIN required: ", resp.message)
                    msg2 = proto.PinMatrixAck(pin=pin)
                    
                return self.call(msg2)

        finally:
            self.transport.session_end()
        
        if isinstance(resp, proto.Failure):
            self.message_func(resp.message)

            if resp.code == proto.Failure_ActionCancelled:
                raise CallException("Action cancelled by user")
                
            elif resp.code == proto.Failure_PinInvalid:
                raise PinException("PIN is invalid")
                
            raise CallException(resp.code, resp.message)
        
        if self.debug:
            print "Received", self._pprint(resp)
            
        return resp
        
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
                if res.request_type == proto.TXOUTPUT:
                    res = self.call(outputs[res.request_index])
                    continue
              
                elif res.request_type == proto.TXINPUT:
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

    def reset_device(self):
        # Begin with device reset workflow
        raise Exception("Not implemented")
        resp = self.call(proto.ResetDevice(random=self._get_local_entropy()))
        self.init_device()
        return isinstance(resp, proto.Success)
    
    def load_device(self, seed, pin):        
        resp = self.call(proto.LoadDevice(seed=seed, pin=pin))
        self.init_device()
        return isinstance(resp, proto.Success)

    def firmware_update(self, fp):
        if self.features.bootloader_mode == False:
            raise Exception("Device must be in bootloader mode")

        resp = self.call(proto.FirmwareErase())
        if isinstance(resp, proto.Failure) and resp.code == proto.Failure_FirmwareError:
            return False

        resp = self.call(proto.FirmwareUpload(payload=fp.read()))
        if isinstance(resp, proto.Success):
            return True

        elif isinstance(resp, proto.Failure) and resp.code == proto.Failure_FirmwareError:
            return False

        raise Exception("Unexpected result " % resp)
