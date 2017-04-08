
# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def deserialize(value: str) -> HDNode:
    '''
    Construct a BIP0032 HD node from a base58-serialized value.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def from_seed(seed: bytes, curve_name: str) -> HDNode:
    '''
    Construct a BIP0032 HD node from a BIP0039 seed value.
    '''
