import sys
from functools import reduce
import binascii

from trezorlib import _ed25519


def combine_keys(pks):
    P = [_ed25519.decodepoint(pk) for pk in pks]
    combine = reduce(_ed25519.edwards, P)
    return _ed25519.encodepoint(combine)


def combine_sig(R, sigs):
    S = [_ed25519.decodeint(si) for si in sigs]
    s = sum(S) % _ed25519.l
    sig = R + _ed25519.encodeint(s)
    return sig


def get_nonce(sk, data, ctr):
    h = _ed25519.H(sk)
    b = _ed25519.b
    r = _ed25519.Hint(bytes([h[i] for i in range(b >> 3, b >> 2)]) + data + binascii.unhexlify('%08x' % ctr))
    R = _ed25519.scalarmult(_ed25519.B, r)
    return r, _ed25519.encodepoint(R)


def verify(signature, digest, pub_key):
    _ed25519.checkvalid(signature, digest, pub_key)


def sign_with_privkey(digest, privkey, global_pubkey, nonce, global_commit):
    h = _ed25519.H(privkey)
    b = _ed25519.b
    a = 2 ** (b - 2) + sum(2 ** i * _ed25519.bit(h, i) for i in range(3, b - 2))
    S = (nonce + _ed25519.Hint(global_commit + global_pubkey + digest) * a) % _ed25519.l
    return _ed25519.encodeint(S)


def self_test(digest):

    def to_hex(by):
        return binascii.hexlify(by).decode()

    N = 3

    digest = binascii.unhexlify(digest)
    print('Digest: %s' % to_hex(digest))
    sks = []
    pks = []
    nonces = []
    commits = []
    sigs = []
    for i in range(0, N):
        print('----- Key %d ------' % (i + 1))
        seckey = (chr(0x41 + i) * 32).encode()
        pubkey = _ed25519.publickey(seckey)
        print('Secret Key: %s' % to_hex(seckey))
        print('Public Key: %s' % to_hex(pubkey))
        sks.append(seckey)
        pks.append(pubkey)
        ctr = 0
        r, R = get_nonce(seckey, digest, ctr)
        print('Local nonce:  %s' % to_hex(_ed25519.encodeint(r)))
        print('Local commit: %s' % to_hex(R))
        nonces.append(r)
        commits.append(R)

    global_pk = combine_keys(pks)
    global_R = combine_keys(commits)
    print('-----------------')
    print('Global pubkey: %s' % to_hex(global_pk))
    print('Global commit: %s' % to_hex(global_R))
    print('-----------------')

    sigs = [sign_with_privkey(digest, sks[i], global_pk, nonces[i], global_R) for i in range(N)]
    for sig in sigs:
        print('Local signature: %s' % to_hex(sig))

    print('-----------------')
    sig = combine_sig(global_R, sigs)
    print('Global sig: %s' % to_hex(sig))
    verify(sig, digest, global_pk)
    print('Valid Signature!')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        self_test(digest=sys.argv[1])
    else:
        self_test(digest='4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b')
