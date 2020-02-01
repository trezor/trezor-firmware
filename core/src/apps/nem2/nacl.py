import math
from ubinascii import unhexlify, hexlify
from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha3_256, sha3_512

def derive_shared_key(salt, private_key, public_key):
    # port functionality from catbuffer
    # https://github.com/nemtech/nem2-sdk-typescript-javascript/blob/master/src/core/crypto/KeyPair.ts#L73
    # https://github.com/nemtech/nem2-sdk-typescript-javascript/blob/master/src/core/crypto/Utilities.ts#L205

    d = prepare_for_scalar_mult(private_key)

    q = [gf(), gf(), gf(), gf()]
    p = [gf(), gf(), gf(), gf()]
    shared_key = [0] * 32

    unpack(q, public_key)
    scalar_mult(p, q, d)
    pack(shared_key, p)

    for i in range(0, 32):
        shared_key[i] ^= salt[i]

    shared_key_hash = sha3_256(bytearray(shared_key), keccak=True).digest()
    return shared_key_hash

def prepare_for_scalar_mult(secret_key):
    d = sha3_512(secret_key, keccak=True).digest()
    e = clamp(bytearray(d))
    return e

def clamp(d):
    d[0] &= 248
    d[31] &= 127
    d[31] |= 64

    return d

def gf(init=None):
    r = [0] * 16
    if (init):
        for i in range(0, len(init)):
            r[i] = init[i]
    return r

def unpack(r, p):
    t = gf()
    chk = gf()
    num = gf()
    den = gf()
    den2 = gf()
    den4 = gf()
    den6 = gf()
    set25519(r[2], gf([1]))
    unpack25519(r[1], p)
    S(num, r[1])
    D = gf([0x78a3, 0x1359, 0x4dca, 0x75eb, 0xd8ab, 0x4141, 0x0a4d,
        0x0070, 0xe898, 0x7779, 0x4079, 0x8cc7, 0xfe73, 0x2b6f, 0x6cee, 0x5203
    ])

    M(den, num, D)
    Z(num, num, r[2])
    A(den, r[2], den)

    S(den2, den)
    S(den4, den2)
    M(den6, den4, den2)
    M(t, den6, num)
    M(t, t, den)
    pow2523(t, t)
    M(t, t, num)
    M(t, t, den)
    M(t, t, den)
    M(r[0], t, den)
    S(chk, r[0])
    M(chk, chk, den)

    if (neq25519(chk, num)):
        I = gf([0xa0b0, 0x4a0e, 0x1b27, 0xc4ee, 0xe478, 0xad2f, 0x1806,
            0x2f43, 0xd7a7, 0x3dfb, 0x0099, 0x2b4d, 0xdf0b, 0x4fc1, 0x2480, 0x2b83,
        ])
        M(r[0], r[0], I)

    S(chk, r[0])
    M(chk, chk, den)
    if (neq25519(chk, num)):
        return -1

    if (par25519(r[0]) != (p[31] >> 7)):
        Z(r[0], gf0, r[0])

    M(r[3], r[0], r[1])
    return 0

def pack(r, p):
    tx = gf()
    ty = gf()
    zi = gf()

    inv25519(zi, p[2])
    M(tx, p[0], zi)
    M(ty, p[1], zi)
    pack25519(r, ty)
    r[31] ^= par25519(tx) << 7

def set25519(r, a):
    for i in range(0, 16):
        r[i] = a[i] | 0

def unpack25519(o, n):
    for i in range(0, 16):
        o[i] = n[2 * i] + (n[2 * i + 1] << 8)
    o[15] &= 0x7fff

def S(o, a):
    M(o, a, a)

def A (o, a, b):
    for i in range(0, 16):
        o[i] = a[i] + b[i]

def Z(o, a, b):
    for i in range(0, 16):
        o[i] = a[i] - b[i]

def M(o, a, b):
    t0 = 0
    t1 = 0
    t2 = 0
    t3 = 0
    t4 = 0
    t5 = 0
    t6 = 0
    t7 = 0
    t8 = 0
    t9 = 0
    t10 = 0
    t11 = 0
    t12 = 0
    t13 = 0
    t14 = 0
    t15 = 0
    t16 = 0
    t17 = 0
    t18 = 0
    t19 = 0
    t20 = 0
    t21 = 0
    t22 = 0
    t23 = 0
    t24 = 0
    t25 = 0
    t26 = 0
    t27 = 0
    t28 = 0
    t29 = 0
    t30 = 0

    v = a[0]
    t0 += v * b[0]
    t1 += v * b[1]
    t2 += v * b[2]
    t3 += v * b[3]
    t4 += v * b[4]
    t5 += v * b[5]
    t6 += v * b[6]
    t7 += v * b[7]
    t8 += v * b[8]
    t9 += v * b[9]
    t10 += v * b[10]
    t11 += v * b[11]
    t12 += v * b[12]
    t13 += v * b[13]
    t14 += v * b[14]
    t15 += v * b[15]

    v = a[1]
    t1 += v * b[0]
    t2 += v * b[1]
    t3 += v * b[2]
    t4 += v * b[3]
    t5 += v * b[4]
    t6 += v * b[5]
    t7 += v * b[6]
    t8 += v * b[7]
    t9 += v * b[8]
    t10 += v * b[9]
    t11 += v * b[10]
    t12 += v * b[11]
    t13 += v * b[12]
    t14 += v * b[13]
    t15 += v * b[14]
    t16 += v * b[15]

    v = a[2]
    t2 += v * b[0]
    t3 += v * b[1]
    t4 += v * b[2]
    t5 += v * b[3]
    t6 += v * b[4]
    t7 += v * b[5]
    t8 += v * b[6]
    t9 += v * b[7]
    t10 += v * b[8]
    t11 += v * b[9]
    t12 += v * b[10]
    t13 += v * b[11]
    t14 += v * b[12]
    t15 += v * b[13]
    t16 += v * b[14]
    t17 += v * b[15]

    v = a[3]
    t3 += v * b[0]
    t4 += v * b[1]
    t5 += v * b[2]
    t6 += v * b[3]
    t7 += v * b[4]
    t8 += v * b[5]
    t9 += v * b[6]
    t10 += v * b[7]
    t11 += v * b[8]
    t12 += v * b[9]
    t13 += v * b[10]
    t14 += v * b[11]
    t15 += v * b[12]
    t16 += v * b[13]
    t17 += v * b[14]
    t18 += v * b[15]

    v = a[4]
    t4 += v * b[0]
    t5 += v * b[1]
    t6 += v * b[2]
    t7 += v * b[3]
    t8 += v * b[4]
    t9 += v * b[5]
    t10 += v * b[6]
    t11 += v * b[7]
    t12 += v * b[8]
    t13 += v * b[9]
    t14 += v * b[10]
    t15 += v * b[11]
    t16 += v * b[12]
    t17 += v * b[13]
    t18 += v * b[14]
    t19 += v * b[15]

    v = a[5]
    t5 += v * b[0]
    t6 += v * b[1]
    t7 += v * b[2]
    t8 += v * b[3]
    t9 += v * b[4]
    t10 += v * b[5]
    t11 += v * b[6]
    t12 += v * b[7]
    t13 += v * b[8]
    t14 += v * b[9]
    t15 += v * b[10]
    t16 += v * b[11]
    t17 += v * b[12]
    t18 += v * b[13]
    t19 += v * b[14]
    t20 += v * b[15]

    v = a[6]
    t6 += v * b[0]
    t7 += v * b[1]
    t8 += v * b[2]
    t9 += v * b[3]
    t10 += v * b[4]
    t11 += v * b[5]
    t12 += v * b[6]
    t13 += v * b[7]
    t14 += v * b[8]
    t15 += v * b[9]
    t16 += v * b[10]
    t17 += v * b[11]
    t18 += v * b[12]
    t19 += v * b[13]
    t20 += v * b[14]
    t21 += v * b[15]

    v = a[7]
    t7 += v * b[0]
    t8 += v * b[1]
    t9 += v * b[2]
    t10 += v * b[3]
    t11 += v * b[4]
    t12 += v * b[5]
    t13 += v * b[6]
    t14 += v * b[7]
    t15 += v * b[8]
    t16 += v * b[9]
    t17 += v * b[10]
    t18 += v * b[11]
    t19 += v * b[12]
    t20 += v * b[13]
    t21 += v * b[14]
    t22 += v * b[15]

    v = a[8]
    t8 += v * b[0]
    t9 += v * b[1]
    t10 += v * b[2]
    t11 += v * b[3]
    t12 += v * b[4]
    t13 += v * b[5]
    t14 += v * b[6]
    t15 += v * b[7]
    t16 += v * b[8]
    t17 += v * b[9]
    t18 += v * b[10]
    t19 += v * b[11]
    t20 += v * b[12]
    t21 += v * b[13]
    t22 += v * b[14]
    t23 += v * b[15]

    v = a[9]
    t9 += v * b[0]
    t10 += v * b[1]
    t11 += v * b[2]
    t12 += v * b[3]
    t13 += v * b[4]
    t14 += v * b[5]
    t15 += v * b[6]
    t16 += v * b[7]
    t17 += v * b[8]
    t18 += v * b[9]
    t19 += v * b[10]
    t20 += v * b[11]
    t21 += v * b[12]
    t22 += v * b[13]
    t23 += v * b[14]
    t24 += v * b[15]

    v = a[10]
    t10 += v * b[0]
    t11 += v * b[1]
    t12 += v * b[2]
    t13 += v * b[3]
    t14 += v * b[4]
    t15 += v * b[5]
    t16 += v * b[6]
    t17 += v * b[7]
    t18 += v * b[8]
    t19 += v * b[9]
    t20 += v * b[10]
    t21 += v * b[11]
    t22 += v * b[12]
    t23 += v * b[13]
    t24 += v * b[14]
    t25 += v * b[15]

    v = a[11]
    t11 += v * b[0]
    t12 += v * b[1]
    t13 += v * b[2]
    t14 += v * b[3]
    t15 += v * b[4]
    t16 += v * b[5]
    t17 += v * b[6]
    t18 += v * b[7]
    t19 += v * b[8]
    t20 += v * b[9]
    t21 += v * b[10]
    t22 += v * b[11]
    t23 += v * b[12]
    t24 += v * b[13]
    t25 += v * b[14]
    t26 += v * b[15]

    v = a[12]
    t12 += v * b[0]
    t13 += v * b[1]
    t14 += v * b[2]
    t15 += v * b[3]
    t16 += v * b[4]
    t17 += v * b[5]
    t18 += v * b[6]
    t19 += v * b[7]
    t20 += v * b[8]
    t21 += v * b[9]
    t22 += v * b[10]
    t23 += v * b[11]
    t24 += v * b[12]
    t25 += v * b[13]
    t26 += v * b[14]
    t27 += v * b[15]

    v = a[13]
    t13 += v * b[0]
    t14 += v * b[1]
    t15 += v * b[2]
    t16 += v * b[3]
    t17 += v * b[4]
    t18 += v * b[5]
    t19 += v * b[6]
    t20 += v * b[7]
    t21 += v * b[8]
    t22 += v * b[9]
    t23 += v * b[10]
    t24 += v * b[11]
    t25 += v * b[12]
    t26 += v * b[13]
    t27 += v * b[14]
    t28 += v * b[15]

    v = a[14]
    t14 += v * b[0]
    t15 += v * b[1]
    t16 += v * b[2]
    t17 += v * b[3]
    t18 += v * b[4]
    t19 += v * b[5]
    t20 += v * b[6]
    t21 += v * b[7]
    t22 += v * b[8]
    t23 += v * b[9]
    t24 += v * b[10]
    t25 += v * b[11]
    t26 += v * b[12]
    t27 += v * b[13]
    t28 += v * b[14]
    t29 += v * b[15]

    v = a[15]
    t15 += v * b[0]
    t16 += v * b[1]
    t17 += v * b[2]
    t18 += v * b[3]
    t19 += v * b[4]
    t20 += v * b[5]
    t21 += v * b[6]
    t22 += v * b[7]
    t23 += v * b[8]
    t24 += v * b[9]
    t25 += v * b[10]
    t26 += v * b[11]
    t27 += v * b[12]
    t28 += v * b[13]
    t29 += v * b[14]
    t30 += v * b[15]
    t0 += 38 * t16
    t1 += 38 * t17
    t2 += 38 * t18
    t3 += 38 * t19
    t4 += 38 * t20
    t5 += 38 * t21
    t6 += 38 * t22
    t7 += 38 * t23
    t8 += 38 * t24
    t9 += 38 * t25
    t10 += 38 * t26
    t11 += 38 * t27
    t12 += 38 * t28
    t13 += 38 * t29
    t14 += 38 * t30

    c = 1
    v = t0 + c + 65535
    c = math.floor(v / 65536)
    t0 = v - c * 65536
    v = t1 + c + 65535
    c = math.floor(v / 65536)
    t1 = v - c * 65536
    v = t2 + c + 65535
    c = math.floor(v / 65536)
    t2 = v - c * 65536
    v = t3 + c + 65535
    c = math.floor(v / 65536)
    t3 = v - c * 65536
    v = t4 + c + 65535
    c = math.floor(v / 65536)
    t4 = v - c * 65536
    v = t5 + c + 65535
    c = math.floor(v / 65536)
    t5 = v - c * 65536
    v = t6 + c + 65535
    c = math.floor(v / 65536)
    t6 = v - c * 65536
    v = t7 + c + 65535
    c = math.floor(v / 65536)
    t7 = v - c * 65536
    v = t8 + c + 65535
    c = math.floor(v / 65536)
    t8 = v - c * 65536
    v = t9 + c + 65535
    c = math.floor(v / 65536)
    t9 = v - c * 65536
    v = t10 + c + 65535
    c = math.floor(v / 65536)
    t10 = v - c * 65536
    v = t11 + c + 65535
    c = math.floor(v / 65536)
    t11 = v - c * 65536
    v = t12 + c + 65535
    c = math.floor(v / 65536)
    t12 = v - c * 65536
    v = t13 + c + 65535
    c = math.floor(v / 65536)
    t13 = v - c * 65536
    v = t14 + c + 65535
    c = math.floor(v / 65536)
    t14 = v - c * 65536
    v = t15 + c + 65535
    c = math.floor(v / 65536)
    t15 = v - c * 65536
    t0 += c - 1 + 37 * (c - 1)

    c = 1
    v = t0 + c + 65535
    c = math.floor(v / 65536)
    t0 = v - c * 65536
    v = t1 + c + 65535
    c = math.floor(v / 65536)
    t1 = v - c * 65536
    v = t2 + c + 65535
    c = math.floor(v / 65536)
    t2 = v - c * 65536
    v = t3 + c + 65535
    c = math.floor(v / 65536)
    t3 = v - c * 65536
    v = t4 + c + 65535
    c = math.floor(v / 65536)
    t4 = v - c * 65536
    v = t5 + c + 65535
    c = math.floor(v / 65536)
    t5 = v - c * 65536
    v = t6 + c + 65535
    c = math.floor(v / 65536)
    t6 = v - c * 65536
    v = t7 + c + 65535
    c = math.floor(v / 65536)
    t7 = v - c * 65536
    v = t8 + c + 65535
    c = math.floor(v / 65536)
    t8 = v - c * 65536
    v = t9 + c + 65535
    c = math.floor(v / 65536)
    t9 = v - c * 65536
    v = t10 + c + 65535
    c = math.floor(v / 65536)
    t10 = v - c * 65536
    v = t11 + c + 65535
    c = math.floor(v / 65536)
    t11 = v - c * 65536
    v = t12 + c + 65535
    c = math.floor(v / 65536)
    t12 = v - c * 65536
    v = t13 + c + 65535
    c = math.floor(v / 65536)
    t13 = v - c * 65536
    v = t14 + c + 65535
    c = math.floor(v / 65536)
    t14 = v - c * 65536
    v = t15 + c + 65535
    c = math.floor(v / 65536)
    t15 = v - c * 65536
    t0 += c - 1 + 37 * (c - 1)

    o[0] = t0
    o[1] = t1
    o[2] = t2
    o[3] = t3
    o[4] = t4
    o[5] = t5
    o[6] = t6
    o[7] = t7
    o[8] = t8
    o[9] = t9
    o[10] = t10
    o[11] = t11
    o[12] = t12
    o[13] = t13
    o[14] = t14
    o[15] = t15

def pow2523(o, i):
    c = gf()
    for a in range(0, 16):
        c[a] = i[a]

    for a in range(250, -1, -1):
        S(c, c)
        if(a != 1):
            M(c, c, i)

    for a in range(0, 16):
        o[a] = c[a]

def crypto_verify_32(x, xi, y, yi):
    return vn(x, xi, y, yi, 32)

def vn(x, xi, y, yi, n):
    d = 0
    for i in range(0, n):
        d |= x[xi + i] ^ y[yi + i]

    return zero_fill_right_shift(1 & (d - 1), 8) - 1

def neq25519(a, b):
    c = [0] * 32
    d = [0] * 32

    pack25519(c, a)
    pack25519(d, b)
    return crypto_verify_32(c, 0, d, 0)

def pack25519(o, n):
    m = gf()
    t = gf()

    for i in range(0, 16):
        t[i] = n[i]

    car25519(t)
    car25519(t)
    car25519(t)

    for j in range(0, 2):
        m[0] = t[0] - 0xffed

        for i in range(1, 15):
            m[i] = t[i] - 0xffff - ((m[i - 1] >> 16) & 1)
            m[i - 1] &= 0xffff

        m[15] = t[15] - 0x7fff - ((m[14] >> 16) & 1)
        b = (m[15] >> 16) & 1
        m[14] &= 0xffff
        sel25519(t, m, 1 - b)

    for i in range(0, 16):
        o[2 * i] = t[i] & 0xff
        o[2 * i + 1] = t[i] >> 8

def sel25519(p, q, b):
    c = ~(b - 1)
    for i in range(0, 16):
        t = c & (p[i] ^ q[i])
        p[i] ^= t
        q[i] ^= t

def car25519(o):
    c = 1
    for i in range(0, 16):
        v = o[i] + c + 65535
        c = math.floor(v / 65536)
        o[i] = v - c * 65536
    o[0] += c - 1 + 37 * (c - 1)

def par25519(a):
    d = [0] * 32
    pack25519(d, a)
    return d[0] & 1

def scalar_mult(p, q, s):
    set25519(p[0], gf([0]))
    set25519(p[1], gf([1]))
    set25519(p[2], gf([1]))
    set25519(p[3], gf([0]))
    for i in range(255, -1, -1):
        b = (s[math.floor(i / 8) | 0] >> (i & 7)) & 1
        cswap(p, q, b)
        add(q, p)
        add(p, p)
        cswap(p, q, b)

def cswap(p, q, b):
    for i in range(0, 4):
        sel25519(p[i], q[i], b)

def inv25519 (o, i):
    c = gf()
    for a in range(0, 16):
        c[a] = i[a]

    for a in range(253, -1, -1):
        S(c, c)
        if(a != 2 and a != 4):
            M(c, c, i)

    for a in range(0, 16):
        o[a] = c[a]

def add(p, q):
    a = gf()
    b = gf()
    c = gf()
    d = gf()
    e = gf()
    f = gf()
    g = gf()
    h = gf()
    t = gf()

    Z(a, p[1], p[0])
    Z(t, q[1], q[0])
    M(a, a, t)
    A(b, p[0], p[1])
    A(t, q[0], q[1])
    M(b, b, t)
    M(c, p[3], q[3])

    D2 = gf([0xf159, 0x26b2, 0x9b94, 0xebd6, 0xb156, 0x8283, 0x149a,
        0x00e0, 0xd130, 0xeef3, 0x80f2, 0x198e, 0xfce7, 0x56df, 0xd9dc, 0x2406,
    ])

    M(c, c, D2)
    M(d, p[2], q[2])
    A(d, d, d)
    Z(e, b, a)
    Z(f, d, c)
    A(g, d, c)
    A(h, b, a)
    M(p[0], e, f)
    M(p[1], h, g)
    M(p[2], g, f)
    M(p[3], e, h)

def zero_fill_right_shift(val, n):
    return (val >> n) if val >= 0 else ((val + 0x100000000) >> n)