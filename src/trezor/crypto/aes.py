from TrezorCrypto import AES as _AES

def AES_ECB_Encrypt(key: bytes):
    '''
    Create AES encryption context in ECB mode
    '''
    return _AES(0x00, key)

def AES_ECB_Decrypt(key: bytes):
    '''
    Create AES decryption context in ECB mode
    '''
    return _AES(0x80, key)

def AES_CBC_Encrypt(key: bytes, iv: bytes):
    '''
    Create AES encryption context in CBC mode
    '''
    return _AES(0x01, key, iv)

def AES_CBC_Decrypt(key: bytes, iv: bytes):
    '''
    Create AES decryption context in CBC mode
    '''
    return _AES(0x81, key, iv)

def AES_CFB_Encrypt(key: bytes, iv: bytes):
    '''
    Create AES encryption context in CFB mode
    '''
    return _AES(0x02, key, iv)

def AES_CFB_Decrypt(key: bytes, iv: bytes):
    '''
    Create AES decryption context in CFB mode
    '''
    return _AES(0x82, key, iv)

def AES_OFB_Encrypt(key: bytes, iv: bytes):
    '''
    Create AES encryption context in OFB mode
    '''
    return _AES(0x03, key, iv)

def AES_OFB_Decrypt(key: bytes, iv: bytes):
    '''
    Create AES decryption context in OFB mode
    '''
    return _AES(0x83, key, iv)

def AES_CTR_Encrypt(key: bytes):
    '''
    Create AES encryption context in CTR mode
    '''
    return _AES(0x04, key)

def AES_CTR_Decrypt(key: bytes):
    '''
    Create AES decryption context in CTR mode
    '''
    return _AES(0x84, key)
