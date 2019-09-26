from trezor.crypto import beam, random

from apps.common import storage


def BBS_KEY():
    return 1113748301


def beam_app_id():
    return 19


def get_master_nonce_idx():
    return 0


def bin_to_str(binary_data):
    return "".join("{:02x}".format(x) for x in binary_data)


def get_beam_kdf(mnemonic=None):
    if mnemonic is None:
        # Get kdf
        mnemonic = storage.device.get_mnemonic_secret()
    seed = beam.from_mnemonic_beam(mnemonic)
    seed_size = 32
    secret_key = bytearray(32)
    cofactor = bytearray(32)
    beam.seed_to_kdf(seed, seed_size, secret_key, cofactor)
    return (secret_key, cofactor)


def get_beam_sk(kid_idx, kid_sub_idx=0, kdf=None):
    # Generate hash id
    kid_type = BBS_KEY()
    hash_id = bytearray(32)
    beam.generate_hash_id(kid_idx, kid_type, kid_sub_idx, hash_id)

    if kdf is None:
        # Get kdf
        secret_key, cofactor = get_beam_kdf()
    else:
        secret_key, cofactor = kdf

    # Derive key
    res_sk = bytearray(32)
    beam.derive_child_key(secret_key, 32, hash_id, 32, cofactor, res_sk)

    return res_sk


def get_beam_pk(kid_idx, kid_sub_idx=0, kdf=None):
    # Secret key to public key
    public_key_x = bytearray(32)
    public_key_y = bytearray(1)
    sk = get_beam_sk(kid_idx, kid_sub_idx, kdf)
    beam.secret_key_to_public_key(sk, public_key_x, public_key_y)

    return (public_key_x, int(public_key_y[0]))


def is_valid_beam_message(signature, public_key, message):
    is_valid = beam.is_valid_signature(
        message,
        signature.nonce_pub.x,
        int(signature.nonce_pub.y),
        signature.sign_k,
        public_key.x,
        int(public_key.y),
    )

    return is_valid


def rand_pswd(size=8):
    """Generate a random password of fixed length """
    charset = "12346789ACDEFGHJKLMNPQRTUVWXYabcdefghijkmnopqrstuvwxyz"
    return "".join(charset[random.uniform(len(charset))] for _ in range(size))
