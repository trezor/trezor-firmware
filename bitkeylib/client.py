import os
import bitkey_pb2 as proto

def show_message(message):
    print "MESSAGE FROM DEVICE:", message
    
def show_input(input_text, message=None):
    if message:
        print "QUESTION FROM DEVICE:", message
    return raw_input(input_text)

class BitkeyClient(object):
    
    def __init__(self, transport, debuglink=None, message_func=show_message, input_func=show_input, debug=False):
        self.master_public_key = None
        self.transport = transport        
        self.debuglink = debuglink
        
        self.message_func = message_func
        self.input_func = input_func
        self.debug = debug

        self.features = self.call(proto.Initialize()) 
        self.UUID = self.call(proto.GetUUID())
                
    def _pprint(self, msg):
        return "<%s>:\n%s" % (msg.__class__.__name__, msg)

    def call(self, msg, tries=1, button=None, pin_correct=True, otp_correct=True):
        if self.debug:
            print '----------------------'
            print "Sending", self._pprint(msg)
        
        self.transport.write(msg)
        
        if self.debuglink and button != None:
            self.debuglink.press_button(button)

        resp = self.transport.read()
                
        if isinstance(resp, proto.OtpRequest):
            if self.debuglink:
                otp = self.debuglink.read_otp()
                if otp_correct:
                    self.transport.write(otp)
                else:
                    self.transport.write(proto.OtpAck(otp='__42__'))
            else:
                otp = self.input_func("OTP required: ", resp.message)
                self.transport.write(proto.OtpAck(otp=otp))
            
            resp = self.transport.read()
    
        if isinstance(resp, proto.PinRequest):
            if self.debuglink:
                pin = self.debuglink.read_pin()
                if pin_correct:
                    self.transport.write(pin)
                else:
                    self.transport.write(proto.PinAck(pin='__42__'))
            else:
                pin = self.input_func("PIN required: ", resp.message)
                self.transport.write(proto.PinAck(pin=pin))
                
            resp = self.transport.read()
        
        if isinstance(resp, proto.Failure):
            self.message_func(resp.message)
            
            if resp.code == 3:
                if tries <= 1:
                    raise Exception("OTP is invalid, too many retries")
                self.message_func("OTP is invalid, let's try again...")
                
            elif resp.code == 4:    
                raise Exception("Action cancelled by user")
                
            elif resp.code == 6:
                if tries <= 1:
                    raise Exception("PIN is invalid, too many retries")
                self.message_func("PIN is invalid, let's try again...")    
                
            return self.call(msg, tries-1,
                             button=button,
                             pin_correct=pin_correct,
                             otp_correct=otp_correct)
    
        if isinstance(resp, proto.Failure):
            raise Exception(resp.code, resp.message)
        
        if self.debug:
            print "Received", self._pprint(resp)
            
        return resp

    def sign_tx(self, algo, inputs, outputs, fee):
        '''
            inputs: list of TxInput
            outputs: list of TxOutput
        '''
            
        tx = proto.SignTx()
        tx.algo = algo # Choose BIP32 or ELECTRUM way for deterministic keys
        tx.random = os.urandom(256) # Provide additional entropy to the device

        for addr, amount in outputs:
            if addr in self.addresses:
                addr_n = self.addresses.index(addr)
            else:
                addr_n = None
            
            fee -= amount
            output = tx.outputs.add()
            output.address=addr
            output.address_n.append(addr_n)
            output.amount=amount
            output.script_type=proto.PAYTOADDRESS
            
        print "FEE", fee
        #print inputs2, outputs2
        
        tx.fee = fee
        print "PBDATA", tx.SerializeToString().encode('hex')
        
        #################
        #################
        #################
        
        signatures = [('add550d6ba9ab7e01d37e17658f98b6e901208d241f24b08197b5e20dfa7f29f095ae01acbfa5c4281704a64053dcb80e9b089ecbe09f5871d67725803e36edd', '3045022100dced96eeb43836bc95676879eac303eabf39802e513f4379a517475c259da12502201fd36c90ecd91a32b2ca8fed2e1755a7f2a89c2d520eb0da10147802bc7ca217')]
        
        s_inputs = []
        for i in range(len(inputs)):
            addr, v, p_hash, p_pos, p_scriptPubKey, _, _ = inputs[i]
            pubkey = signatures[i][0].decode('hex')
            sig = signatures[i][1].decode('hex')
            s_inputs.append((addr, v, p_hash, p_pos, p_scriptPubKey, pubkey, sig))
        
        return s_inputs
        '''        
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
