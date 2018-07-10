from trezorcrypto import AES


def AES_ECB_Encrypt(key: bytes) -> AES:
    """
    Create AES encryption context in ECB mode
    """
    return AES(AES.ECB | AES.Encrypt, key)


def AES_ECB_Decrypt(key: bytes) -> AES:
    """
    Create AES decryption context in ECB mode
    """
    return AES(AES.ECB | AES.Decrypt, key)


def AES_CBC_Encrypt(key: bytes, iv: bytes) -> AES:
    """
    Create AES encryption context in CBC mode
    """
    return AES(AES.CBC | AES.Encrypt, key, iv)


def AES_CBC_Decrypt(key: bytes, iv: bytes) -> AES:
    """
    Create AES decryption context in CBC mode
    """
    return AES(AES.CBC | AES.Decrypt, key, iv)


def AES_CFB_Encrypt(key: bytes, iv: bytes) -> AES:
    """
    Create AES encryption context in CFB mode
    """
    return AES(AES.CFB | AES.Encrypt, key, iv)


def AES_CFB_Decrypt(key: bytes, iv: bytes) -> AES:
    """
    Create AES decryption context in CFB mode
    """
    return AES(AES.CFB | AES.Decrypt, key, iv)


def AES_OFB_Encrypt(key: bytes, iv: bytes) -> AES:
    """
    Create AES encryption context in OFB mode
    """
    return AES(AES.OFB | AES.Encrypt, key, iv)


def AES_OFB_Decrypt(key: bytes, iv: bytes) -> AES:
    """
    Create AES decryption context in OFB mode
    """
    return AES(AES.OFB | AES.Decrypt, key, iv)


def AES_CTR_Encrypt(key: bytes) -> AES:
    """
    Create AES encryption context in CTR mode
    """
    return AES(AES.CTR | AES.Encrypt, key)


def AES_CTR_Decrypt(key: bytes) -> AES:
    """
    Create AES decryption context in CTR mode
    """
    return AES(AES.CTR | AES.Decrypt, key)
