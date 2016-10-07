
# ../extmod/modtrezorcrypto/modtrezorcrypto-pbkdf2.h
def pbkdf2(prf: str, password: bytes, salt: bytes, iterations: int=None) -> Pbkdf2:
    '''
    Create a PBKDF2 context
    '''
