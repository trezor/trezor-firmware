import sys
from functools import reduce
import binascii

from . import ed25519raw


def combine_keys(pks):
    P = [ed25519raw.decodepoint(pk) for pk in pks]
    combine = reduce(ed25519raw.edwards, P)
    return ed25519raw.encodepoint(combine)


def combine_sig(R, sigs):
    S = [ed25519raw.decodeint(si) for si in sigs]
    s = sum(S) % ed25519raw.l
    sig = R + ed25519raw.encodeint(s)
    return sig


def get_nonce(sk, data, ctr):
    h = ed25519raw.H(sk)
    b = ed25519raw.b
    r = ed25519raw.Hint(bytes([h[i] for i in range(b >> 3, b >> 2)]) + data + binascii.unhexlify('%08x' % ctr))
    R = ed25519raw.scalarmult(ed25519raw.B, r)
    return r, ed25519raw.encodepoint(R)


def self_test(digest):

    def to_hex(by):
        return binascii.hexlify(by).decode()

    N = 3
    keyset = [0, 2]

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
        pubkey = ed25519raw.publickey(seckey)
        print('Secret Key: %s' % to_hex(seckey))
        print('Public Key: %s' % to_hex(pubkey))
        sks.append(seckey)
        pks.append(pubkey)
        ctr = 0
        r, R = get_nonce(seckey, digest, ctr)
        print('Local nonce:  %s' % to_hex(ed25519raw.encodeint(r)))
        print('Local commit: %s' % to_hex(R))
        nonces.append(r)
        commits.append(R)

    global_pk = combine_keys([pks[i] for i in keyset])
    global_R = combine_keys([commits[i] for i in keyset])
    print('-----------------')
    print('Global pubkey: %s' % to_hex(global_pk))
    print('Global commit: %s' % to_hex(global_R))
    print('-----------------')

    for i in range(0, N):
        seckey = sks[i]
        pubkey = pks[i]
        r = nonces[i]
        R = commits[i]
        h = ed25519raw.H(seckey)
        b = ed25519raw.b
        a = 2**(b - 2) + sum(2**i * ed25519raw.bit(h, i) for i in range(3, b - 2))
        S = (r + ed25519raw.Hint(global_R + global_pk + digest) * a) % ed25519raw.l
        print('Local sig %d: %s' % (i + 1, to_hex(ed25519raw.encodeint(S))))
        sigs.append(ed25519raw.encodeint(S))

    print('-----------------')
    sig = combine_sig(global_R, [sigs[i] for i in keyset])
    print('Global sig: %s' % to_hex(sig))
    ed25519raw.checkvalid(sig, digest, global_pk)
    print('Valid Signature!')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        self_test(digest=sys.argv[1])
    else:
        self_test(digest='4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b')
