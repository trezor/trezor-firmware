from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-beam.h
class TransactionMaker:
    '''
    TransactionMaker serves as a facade to build and sign the transaction
    '''
    def __init__(self):
        '''
        Creates TransactionMaker object
        '''
    def add_input(self, input: KeyIDV):
        '''
        Adds input to the transaction
        '''
    def add_output(self, output: KeyIDV):
        '''
        Adds output to the transaction
        '''
    def sign_transaction(self, seed: bytes):
        '''
        Signs transaction with kdf createn from given seed
        '''
    def set_transaction_data(self,
                             fee: uint,
                             min_height: uint, max_height: uint,
                             commitment_x: bytes, commitment_y: uint,
                             nonce_x: bytes, nonce_y: uint,
                             nonce_slot: uint,
                             sk_offset: bytes):
        '''
        Sets fields for transaction data
        '''


# extmod/modtrezorcrypto/modtrezorcrypto-beam.h
class KeyIDV:
    '''
    Beam KeyIDV
    '''
    def __init__(self):
        '''
        Creates a KIDV object.
        '''
    def set(self, idx: uint, type: uint, sub_idx: uint, value: uint):
        '''
        Sets index, type, sub index and value of KIDV object.
        '''

    def from_mnemonic_beam(mnemonic: str) -> bytes:
        '''
        Generate BEAM seed from mnemonic and passphrase.
        '''

    def generate_hash_id(idx: int, type: int, sub_idx: int, out32: bytes):
        '''
        Generate BEAM hash id.
        '''

    def seed_to_kdf(seed: bytes, seed_size: int, out_gen32: bytes, out_cofactor:
    bytes):
        '''
        Transform seed to BEAM KDF
        '''
