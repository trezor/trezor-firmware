import bitkey_pb2 as proto

map_type_to_class = {
       0: proto.Initialize,
       1: proto.Ping,
       2: proto.Success,
       3: proto.Failure,
       4: proto.GetUUID,
       5: proto.UUID,
       6: proto.OtpRequest,
       7: proto.OtpAck,
       8: proto.OtpCancel,
       9: proto.GetEntropy,
       10: proto.Entropy,
       11: proto.GetMasterPublicKey,
       12: proto.MasterPublicKey,
       13: proto.LoadDevice,
       14: proto.ResetDevice,
       15: proto.SignTx,
#       16: proto.SignedTx,
       17: proto.Features,
       18: proto.PinRequest,
       19: proto.PinAck,
       20: proto.PinCancel,
       21: proto.TxRequest,
       #22: proto.OutputRequest,
       23: proto.TxInput,
       24: proto.TxOutput,
       25: proto.SetMaxFeeKb,
       26: proto.ButtonRequest,
       27: proto.ButtonAck,
       28: proto.ButtonCancel,
       29: proto.GetAddress,
       30: proto.Address,
       100: proto.DebugLinkDecision,
       101: proto.DebugLinkGetState,
       102: proto.DebugLinkState,
}

map_class_to_type = {}

def get_type(msg):
    return map_class_to_type[msg.__class__]

def get_class(t):
    return map_type_to_class[t]

def build_index():
    for k, v in map_type_to_class.items():
        map_class_to_type[v] = k
            
def check_missing():
    from google.protobuf import reflection
    
    types = [ proto.__dict__[item] for item in dir(proto)
                if issubclass(proto.__dict__[item].__class__, reflection.GeneratedProtocolMessageType) ]
    
    missing = list(set(types) - set(map_type_to_class.values()))

    if len(missing):
        raise Exception("Following protobuf messages are not defined in mapping: %s" % missing)

check_missing()
build_index()
