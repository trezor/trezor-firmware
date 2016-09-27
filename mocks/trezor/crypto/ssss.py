
# ../extmod/modtrezorcrypto/modtrezorcrypto-ssss.h
def split(m: int, n: int, secret: bytes) -> tuple:
    '''
    Split secret to (M of N) shares using Shamir's Secret Sharing Scheme
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-ssss.h
def combine(shares: tuple) -> bytes:
    '''
    Combine M shares of Shamir's Secret Sharing Scheme into secret
    '''
