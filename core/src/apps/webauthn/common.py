from micropython import const

# COSE Key Object Parameter labels
COSE_KEY_KTY = const(1)  # identification of the key type
COSE_KEY_ALG = const(3)  # algorithm to be used with the key
COSE_KEY_CRV = const(-1)  # elliptic curve identifier
COSE_KEY_X = const(-2)  # x coordinate of the public key or encoded public key
COSE_KEY_Y = const(-3)  # y coordinate of the public key

# COSE Algorithm values
COSE_ALG_ES256 = const(-7)  # ECDSA with SHA-256
COSE_ALG_EDDSA = const(-8)  # EdDSA
COSE_ALG_ECDH_ES_HKDF_256 = const(-25)  # ephemeral-static ECDH with HKDF SHA-256

# COSE Key Type values
COSE_KEYTYPE_OKP = const(1)  # octet key pair
COSE_KEYTYPE_EC2 = const(2)  # elliptic curve keys with x- and y-coordinate pair

# COSE Elliptic Curve values
COSE_CURVE_P256 = const(1)  # NIST P-256 curve
COSE_CURVE_ED25519 = const(6)  # Ed25519 curve
