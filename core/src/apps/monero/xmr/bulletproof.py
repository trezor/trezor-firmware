import gc

from trezor import utils
from trezor.utils import memcpy as _memcpy

from apps.monero.xmr import crypto
from apps.monero.xmr.serialize.int_serialize import dump_uvarint_b_into, uvarint_size

# Constants

BP_LOG_N = 6
BP_N = 64  # 1 << BP_LOG_N
BP_M = 16  # maximal number of bulletproofs

ZERO = b"\x00" * 32
ONE = b"\x01" + b"\x00" * 31
TWO = b"\x02" + b"\x00" * 31
EIGHT = b"\x08" + b"\x00" * 31
INV_EIGHT = crypto.INV_EIGHT
MINUS_ONE = b"\xec\xd3\xf5\x5c\x1a\x63\x12\x58\xd6\x9c\xf7\xa2\xde\xf9\xde\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10"
MINUS_INV_EIGHT = b"\x74\xa4\x19\x7a\xf0\x7d\x0b\xf7\x05\xc2\xda\x25\x2b\x5c\x0b\x0d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0a"

# Monero H point
XMR_H = b"\x8b\x65\x59\x70\x15\x37\x99\xaf\x2a\xea\xdc\x9f\xf1\xad\xd0\xea\x6c\x72\x51\xd5\x41\x54\xcf\xa9\x2c\x17\x3a\x0d\xd3\x9c\x1f\x94"
XMR_HP = crypto.xmr_H()

# get_exponent(Gi[i], XMR_H, i * 2 + 1)
BP_GI_PRE = crypto.tcry.BP_GI_PRE

# get_exponent(Hi[i], XMR_H, i * 2)
BP_HI_PRE = crypto.tcry.BP_HI_PRE

# twoN = vector_powers(TWO, BP_N);
BP_TWO_N = crypto.tcry.BP_TWO_N

# ip12 = inner_product(oneN, twoN);
BP_IP12 = b"\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"


#
# Rct keys operations
# tmp_x are global working registers to minimize memory allocations / heap fragmentation.
# Caution has to be exercised when using the registers and operations using the registers
#

tmp_bf_0 = bytearray(32)
tmp_bf_1 = bytearray(32)
tmp_bf_2 = bytearray(32)
tmp_bf_exp = bytearray(11 + 32 + 4)
tmp_bf_exp_mv = memoryview(tmp_bf_exp)

tmp_pt_1 = crypto.new_point()
tmp_pt_2 = crypto.new_point()
tmp_pt_3 = crypto.new_point()
tmp_pt_4 = crypto.new_point()

tmp_sc_1 = crypto.new_scalar()
tmp_sc_2 = crypto.new_scalar()
tmp_sc_3 = crypto.new_scalar()
tmp_sc_4 = crypto.new_scalar()


def _ensure_dst_key(dst=None):
    if dst is None:
        dst = bytearray(32)
    return dst


def memcpy(dst, dst_off, src, src_off, len):
    if dst is not None:
        _memcpy(dst, dst_off, src, src_off, len)
    return dst


def alloc_scalars(num=1):
    return (crypto.new_scalar() for _ in range(num))


def copy_key(dst, src):
    for i in range(32):
        dst[i] = src[i]
    return dst


def init_key(val, dst=None):
    dst = _ensure_dst_key(dst)
    return copy_key(dst, val)


def gc_iter(i):
    if i & 127 == 0:
        gc.collect()


def invert(dst, x):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(tmp_sc_1, x)
    crypto.sc_inv_into(tmp_sc_2, tmp_sc_1)
    crypto.encodeint_into(dst, tmp_sc_2)
    return dst


def scalarmult_key(dst, P, s):
    dst = _ensure_dst_key(dst)
    crypto.decodepoint_into(tmp_pt_1, P)
    crypto.decodeint_into_noreduce(tmp_sc_1, s)
    crypto.scalarmult_into(tmp_pt_2, tmp_pt_1, tmp_sc_1)
    crypto.encodepoint_into(dst, tmp_pt_2)
    return dst


def scalarmultH(dst, x):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into(tmp_sc_1, x)
    crypto.scalarmult_into(tmp_pt_1, XMR_HP, tmp_sc_1)
    crypto.encodepoint_into(dst, tmp_pt_1)
    return dst


def scalarmult_base(dst, x):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(tmp_sc_1, x)
    crypto.scalarmult_base_into(tmp_pt_1, tmp_sc_1)
    crypto.encodepoint_into(dst, tmp_pt_1)
    return dst


def sc_gen(dst=None):
    dst = _ensure_dst_key(dst)
    crypto.random_scalar(tmp_sc_1)
    crypto.encodeint_into(dst, tmp_sc_1)
    return dst


def sc_add(dst, a, b):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(tmp_sc_1, a)
    crypto.decodeint_into_noreduce(tmp_sc_2, b)
    crypto.sc_add_into(tmp_sc_3, tmp_sc_1, tmp_sc_2)
    crypto.encodeint_into(dst, tmp_sc_3)
    return dst


def sc_sub(dst, a, b):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(tmp_sc_1, a)
    crypto.decodeint_into_noreduce(tmp_sc_2, b)
    crypto.sc_sub_into(tmp_sc_3, tmp_sc_1, tmp_sc_2)
    crypto.encodeint_into(dst, tmp_sc_3)
    return dst


def sc_mul(dst, a, b):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(tmp_sc_1, a)
    crypto.decodeint_into_noreduce(tmp_sc_2, b)
    crypto.sc_mul_into(tmp_sc_3, tmp_sc_1, tmp_sc_2)
    crypto.encodeint_into(dst, tmp_sc_3)
    return dst


def sc_muladd(dst, a, b, c):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(tmp_sc_1, a)
    crypto.decodeint_into_noreduce(tmp_sc_2, b)
    crypto.decodeint_into_noreduce(tmp_sc_3, c)
    crypto.sc_muladd_into(tmp_sc_4, tmp_sc_1, tmp_sc_2, tmp_sc_3)
    crypto.encodeint_into(dst, tmp_sc_4)
    return dst


def sc_mulsub(dst, a, b, c):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(tmp_sc_1, a)
    crypto.decodeint_into_noreduce(tmp_sc_2, b)
    crypto.decodeint_into_noreduce(tmp_sc_3, c)
    crypto.sc_mulsub_into(tmp_sc_4, tmp_sc_1, tmp_sc_2, tmp_sc_3)
    crypto.encodeint_into(dst, tmp_sc_4)
    return dst


def add_keys(dst, A, B):
    dst = _ensure_dst_key(dst)
    crypto.decodepoint_into(tmp_pt_1, A)
    crypto.decodepoint_into(tmp_pt_2, B)
    crypto.point_add_into(tmp_pt_3, tmp_pt_1, tmp_pt_2)
    crypto.encodepoint_into(dst, tmp_pt_3)
    return dst


def sub_keys(dst, A, B):
    dst = _ensure_dst_key(dst)
    crypto.decodepoint_into(tmp_pt_1, A)
    crypto.decodepoint_into(tmp_pt_2, B)
    crypto.point_sub_into(tmp_pt_3, tmp_pt_1, tmp_pt_2)
    crypto.encodepoint_into(dst, tmp_pt_3)
    return dst


def add_keys2(dst, a, b, B):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(tmp_sc_1, a)
    crypto.decodeint_into_noreduce(tmp_sc_2, b)
    crypto.decodepoint_into(tmp_pt_1, B)
    crypto.add_keys2_into(tmp_pt_2, tmp_sc_1, tmp_sc_2, tmp_pt_1)
    crypto.encodepoint_into(dst, tmp_pt_2)
    return dst


def add_keys3(dst, a, A, b, B):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(tmp_sc_1, a)
    crypto.decodeint_into_noreduce(tmp_sc_2, b)
    crypto.decodepoint_into(tmp_pt_1, A)
    crypto.decodepoint_into(tmp_pt_2, B)
    crypto.add_keys3_into(tmp_pt_3, tmp_sc_1, tmp_pt_1, tmp_sc_2, tmp_pt_2)
    crypto.encodepoint_into(dst, tmp_pt_3)
    return dst


def hash_to_scalar(dst, data):
    dst = _ensure_dst_key(dst)
    crypto.hash_to_scalar_into(tmp_sc_1, data)
    crypto.encodeint_into(dst, tmp_sc_1)
    return dst


def hash_vct_to_scalar(dst, data):
    dst = _ensure_dst_key(dst)
    ctx = crypto.get_keccak()
    for x in data:
        ctx.update(x)
    hsh = ctx.digest()

    crypto.decodeint_into(tmp_sc_1, hsh)
    crypto.encodeint_into(tmp_bf_1, tmp_sc_1)
    copy_key(dst, tmp_bf_1)
    return dst


def get_exponent(dst, base, idx):
    dst = _ensure_dst_key(dst)
    salt = b"bulletproof"
    idx_size = uvarint_size(idx)
    final_size = len(salt) + 32 + idx_size
    buff = tmp_bf_exp_mv
    memcpy(buff, 0, base, 0, 32)
    memcpy(buff, 32, salt, 0, len(salt))
    dump_uvarint_b_into(idx, buff, 32 + len(salt))
    crypto.keccak_hash_into(tmp_bf_1, buff[:final_size])
    crypto.hash_to_point_into(tmp_pt_1, tmp_bf_1)
    crypto.encodepoint_into(dst, tmp_pt_1)
    return dst


#
# Key Vectors
#


class KeyVBase:
    """
    Base KeyVector object
    """

    def __init__(self, elems=64):
        self.current_idx = 0
        self.size = elems

    def idxize(self, idx):
        if idx < 0:
            idx = self.size + idx
        if idx >= self.size:
            raise IndexError("Index out of bounds")
        return idx

    def __getitem__(self, item):
        raise ValueError("Not supported")

    def __setitem__(self, key, value):
        raise ValueError("Not supported")

    def __iter__(self):
        self.current_idx = 0
        return self

    def __next__(self):
        if self.current_idx >= self.size:
            raise StopIteration
        else:
            self.current_idx += 1
            return self[self.current_idx - 1]

    def __len__(self):
        return self.size

    def to(self, idx, buff, offset=0):
        return memcpy(buff, offset, self[self.idxize(idx)], 0, 32)

    def read(self, idx, buff, offset=0):
        raise ValueError

    def slice(self, res, start, stop):
        for i in range(start, stop):
            res[i - start] = self[i]
        return res

    def slice_view(self, start, stop):
        return KeyVSliced(self, start, stop)


class KeyV(KeyVBase):
    """
    KeyVector abstraction
    Constant precomputed buffers = bytes, frozen. Same operation as normal.

    Non-constant KeyVector is separated to 64 elements chunks to avoid problems with
    the heap fragmentation. In this way the chunks are more probable to be correctly
    allocated as smaller chunk of continuous memory is required. Chunk is assumed to
    have 64 elements at all times to minimize corner cases handling. BP require either
    multiple of 64 elements vectors or less than 64.

    Some chunk-dependent cases are not implemented as they are currently not needed in the BP.
    """

    def __init__(self, elems=64, buffer=None, const=False, no_init=False):
        super().__init__(elems)
        self.d = None
        self.mv = None
        self.const = const
        self.cur = _ensure_dst_key()
        self.chunked = False
        if no_init:
            pass
        elif buffer:
            self.d = buffer  # can be immutable (bytes)
            self.size = len(buffer) // 32
        else:
            self._set_d(elems)

        if not no_init:
            self._set_mv()

    def _set_d(self, elems):
        if elems > 64 and elems % 64 == 0:
            self.chunked = True
            gc.collect()
            self.d = [bytearray(32 * 64) for _ in range(elems // 64)]

        else:
            self.chunked = False
            gc.collect()
            self.d = bytearray(32 * elems)

    def _set_mv(self):
        if not self.chunked:
            self.mv = memoryview(self.d)

    def __getitem__(self, item):
        """
        Returns corresponding 32 byte array.
        Creates new memoryview on access.
        """
        if self.chunked:
            raise ValueError("Not supported")  # not needed
        item = self.idxize(item)
        return self.mv[item * 32 : (item + 1) * 32]

    def __setitem__(self, key, value):
        if self.chunked:
            raise ValueError("Not supported")  # not needed
        if self.const:
            raise ValueError("Constant KeyV")
        ck = self[key]
        for i in range(32):
            ck[i] = value[i]

    def to(self, idx, buff=None, offset=0):
        idx = self.idxize(idx)
        if self.chunked:
            memcpy(
                buff if buff else self.cur,
                offset,
                self.d[idx >> 6],
                (idx & 63) << 5,
                32,
            )
        else:
            memcpy(buff if buff else self.cur, offset, self.d, idx << 5, 32)
        return buff if buff else self.cur

    def read(self, idx, buff, offset=0):
        idx = self.idxize(idx)
        if self.chunked:
            memcpy(self.d[idx >> 6], (idx & 63) << 5, buff, offset, 32)
        else:
            memcpy(self.d, idx << 5, buff, offset, 32)

    def resize(self, nsize, chop=False, realloc=False):
        if self.size == nsize:
            return self

        if self.chunked and nsize <= 64:
            self.chunked = False  # de-chunk
            if self.size > nsize and realloc:
                gc.collect()
                self.d = bytearray(self.d[0][: nsize << 5])
            elif self.size > nsize and not chop:
                gc.collect()
                self.d = self.d[0][: nsize << 5]
            else:
                gc.collect()
                self.d = bytearray(nsize << 5)

        elif self.chunked:
            raise ValueError("Unsupported")  # not needed

        else:
            if self.size > nsize and realloc:
                gc.collect()
                self.d = bytearray(self.d[: nsize << 5])
            elif self.size > nsize and not chop:
                gc.collect()
                self.d = self.d[: nsize << 5]
            else:
                gc.collect()
                self.d = bytearray(nsize << 5)

        self.size = nsize
        self._set_mv()

    def realloc(self, nsize, collect=False):
        self.d = None
        self.mv = None
        if collect:
            gc.collect()  # gc collect prev. allocation

        self._set_d(nsize)
        self.size = nsize
        self._set_mv()

    def realloc_init_from(self, nsize, src, offset=0, collect=False):
        if not isinstance(src, KeyV):
            raise ValueError("KeyV supported only")
        self.realloc(nsize, collect)

        if not self.chunked and not src.chunked:
            memcpy(self.d, 0, src.d, offset << 5, nsize << 5)

        elif self.chunked and not src.chunked:
            raise ValueError("Unsupported")  # not needed

        elif self.chunked and src.chunked:
            raise ValueError("Unsupported")  # not needed

        elif not self.chunked and src.chunked:
            for i in range(nsize >> 6):
                memcpy(
                    self.d,
                    i << 11,
                    src.d[i + (offset >> 6)],
                    (offset & 63) << 5 if i == 0 else 0,
                    nsize << 5 if i <= nsize >> 6 else (nsize & 64) << 5,
                )


class KeyVEval(KeyVBase):
    """
    KeyVector computed / evaluated on demand
    """

    def __init__(self, elems=64, src=None):
        super().__init__(elems)
        self.fnc = src
        self.buff = _ensure_dst_key()
        self.mv = memoryview(self.buff)

    def __getitem__(self, item):
        return self.fnc(self.idxize(item), self.buff)

    def to(self, idx, buff=None, offset=0):
        self.fnc(self.idxize(idx), self.buff)
        memcpy(buff, offset, self.buff, 0, 32)
        return buff if buff else self.buff


class KeyVSized(KeyVBase):
    """
    Resized vector, wrapping possibly larger vector
    (e.g., precomputed, but has to have exact size for further computations)
    """

    def __init__(self, wrapped, new_size):
        super().__init__(new_size)
        self.wrapped = wrapped

    def __getitem__(self, item):
        return self.wrapped[self.idxize(item)]

    def __setitem__(self, key, value):
        self.wrapped[self.idxize(key)] = value


class KeyVConst(KeyVBase):
    def __init__(self, size, elem, copy=True):
        super().__init__(size)
        self.elem = init_key(elem) if copy else elem

    def __getitem__(self, item):
        return self.elem

    def to(self, idx, buff=None, offset=0):
        memcpy(buff, offset, self.elem, 0, 32)
        return buff if buff else self.elem


class KeyVPrecomp(KeyVBase):
    """
    Vector with possibly large size and some precomputed prefix.
    Usable for Gi vector with precomputed usual sizes (i.e., 2 output transactions)
    but possible to compute further
    """

    def __init__(self, size, precomp_prefix, aux_comp_fnc):
        super().__init__(size)
        self.precomp_prefix = precomp_prefix
        self.aux_comp_fnc = aux_comp_fnc
        self.buff = _ensure_dst_key()

    def __getitem__(self, item):
        item = self.idxize(item)
        if item < len(self.precomp_prefix):
            return self.precomp_prefix[item]
        return self.aux_comp_fnc(item, self.buff)

    def to(self, idx, buff=None, offset=0):
        item = self.idxize(idx)
        if item < len(self.precomp_prefix):
            return self.precomp_prefix.to(item, buff if buff else self.buff, offset)
        self.aux_comp_fnc(item, self.buff)
        memcpy(buff, offset, self.buff, 0, 32)
        return buff if buff else self.buff


class KeyVSliced(KeyVBase):
    """
    Sliced in-memory vector version, remapping
    """

    def __init__(self, src, start, stop):
        super().__init__(stop - start)
        self.wrapped = src
        self.offset = start

    def __getitem__(self, item):
        return self.wrapped[self.offset + self.idxize(item)]

    def __setitem__(self, key, value):
        self.wrapped[self.offset + self.idxize(key)] = value

    def resize(self, nsize, chop=False):
        raise ValueError("Not supported")

    def to(self, idx, buff=None, offset=0):
        return self.wrapped.to(self.offset + self.idxize(idx), buff, offset)

    def read(self, idx, buff, offset=0):
        return self.wrapped.read(self.offset + self.idxize(idx), buff, offset)


class KeyVPowers(KeyVBase):
    """
    Vector of x^i. Allows only sequential access (no jumping). Resets on [0,1] access.
    """

    def __init__(self, size, x, **kwargs):
        super().__init__(size)
        self.x = x
        self.cur = bytearray(32)
        self.last_idx = 0

    def __getitem__(self, item):
        prev = self.last_idx
        item = self.idxize(item)
        self.last_idx = item

        if item == 0:
            return copy_key(self.cur, ONE)
        elif item == 1:
            return copy_key(self.cur, self.x)
        elif item == prev + 1:
            return sc_mul(self.cur, self.cur, self.x)
        else:
            raise IndexError("Only linear scan allowed")


class KeyVZtwo(KeyVBase):
    """
    Ztwo vector - see vector_z_two_i
    """

    def __init__(self, N, logN, M, zpow, twoN, raw=False):
        super().__init__(N * M)
        self.N = N
        self.logN = logN
        self.M = M
        self.zpow = zpow
        self.twoN = twoN
        self.raw = raw
        self.sc = crypto.new_scalar()
        self.cur = bytearray(32) if not raw else None

    def __getitem__(self, item):
        vector_z_two_i(self.logN, self.zpow, self.twoN, self.idxize(item), self.sc)
        if self.raw:
            return self.sc

        crypto.encodeint_into(self.cur, self.sc)
        return self.cur


def _ensure_dst_keyvect(dst=None, size=None):
    if dst is None:
        dst = KeyV(elems=size)
        return dst
    if size is not None and size != len(dst):
        dst.resize(size)
    return dst


def const_vector(val, elems=BP_N, copy=True):
    return KeyVConst(elems, val, copy)


def vector_exponent_custom(A, B, a, b, dst=None):
    dst = _ensure_dst_key(dst)
    crypto.identity_into(tmp_pt_2)

    for i in range(len(a)):
        crypto.decodeint_into_noreduce(tmp_sc_1, a.to(i))
        crypto.decodepoint_into(tmp_pt_3, A.to(i))
        crypto.decodeint_into_noreduce(tmp_sc_2, b.to(i))
        crypto.decodepoint_into(tmp_pt_4, B.to(i))
        crypto.add_keys3_into(tmp_pt_1, tmp_sc_1, tmp_pt_3, tmp_sc_2, tmp_pt_4)
        crypto.point_add_into(tmp_pt_2, tmp_pt_2, tmp_pt_1)
        gc_iter(i)
    crypto.encodepoint_into(dst, tmp_pt_2)
    return dst


def vector_powers(x, n, dst=None, dynamic=False, **kwargs):
    if dynamic:
        return KeyVPowers(n, x, **kwargs)
    dst = _ensure_dst_keyvect(dst, n)
    if n == 0:
        return dst
    dst.read(0, ONE)
    if n == 1:
        return dst
    dst.read(1, x)

    crypto.decodeint_into_noreduce(tmp_sc_1, x)
    crypto.decodeint_into_noreduce(tmp_sc_2, x)
    for i in range(2, n):
        crypto.sc_mul_into(tmp_sc_1, tmp_sc_1, tmp_sc_2)
        crypto.encodeint_into(tmp_bf_0, tmp_sc_1)
        dst.read(i, tmp_bf_0)
        gc_iter(i)
    return dst


def vector_power_sum(x, n, dst=None):
    dst = _ensure_dst_key(dst)
    if n == 0:
        return copy_key(dst, ZERO)

    copy_key(dst, ONE)
    if n == 1:
        return dst

    prev = init_key(x)
    for i in range(1, n):
        if i > 1:
            sc_mul(prev, prev, x)
        sc_add(dst, dst, prev)
        gc_iter(i)
    return dst


def inner_product(a, b, dst=None):
    if len(a) != len(b):
        raise ValueError("Incompatible sizes of a and b")
    dst = _ensure_dst_key(dst)
    crypto.sc_init_into(tmp_sc_1, 0)

    for i in range(len(a)):
        crypto.decodeint_into_noreduce(tmp_sc_2, a.to(i))
        crypto.decodeint_into_noreduce(tmp_sc_3, b.to(i))
        crypto.sc_muladd_into(tmp_sc_1, tmp_sc_2, tmp_sc_3, tmp_sc_1)
        gc_iter(i)

    crypto.encodeint_into(dst, tmp_sc_1)
    return dst


def hadamard(a, b, dst=None):
    dst = _ensure_dst_keyvect(dst, len(a))
    for i in range(len(a)):
        sc_mul(tmp_bf_1, a.to(i), b.to(i))
        dst.read(i, tmp_bf_1)
        gc_iter(i)
    return dst


def hadamard_fold(v, a, b, into=None, into_offset=0):
    """
    Folds a curvepoint array using a two way scaled Hadamard product

    ln = len(v); h = ln // 2
    v[i] = a * v[i] + b * v[h + i]
    """
    h = len(v) // 2
    crypto.decodeint_into_noreduce(tmp_sc_1, a)
    crypto.decodeint_into_noreduce(tmp_sc_2, b)
    into = into if into else v

    for i in range(h):
        crypto.decodepoint_into(tmp_pt_1, v.to(i))
        crypto.decodepoint_into(tmp_pt_2, v.to(h + i))
        crypto.add_keys3_into(tmp_pt_3, tmp_sc_1, tmp_pt_1, tmp_sc_2, tmp_pt_2)
        crypto.encodepoint_into(tmp_bf_0, tmp_pt_3)
        into.read(i + into_offset, tmp_bf_0)
        gc_iter(i)

    return into


def scalar_fold(v, a, b, into=None, into_offset=0):
    """
    ln = len(v); h = ln // 2
    v[i] = v[i] * a + v[h+i] * b)
    """
    h = len(v) // 2
    crypto.decodeint_into_noreduce(tmp_sc_1, a)
    crypto.decodeint_into_noreduce(tmp_sc_2, b)
    into = into if into else v

    for i in range(h):
        crypto.decodeint_into_noreduce(tmp_sc_3, v.to(i))
        crypto.decodeint_into_noreduce(tmp_sc_4, v.to(h + i))
        crypto.sc_mul_into(tmp_sc_3, tmp_sc_3, tmp_sc_1)
        crypto.sc_mul_into(tmp_sc_4, tmp_sc_4, tmp_sc_2)
        crypto.sc_add_into(tmp_sc_3, tmp_sc_3, tmp_sc_4)
        crypto.encodeint_into(tmp_bf_0, tmp_sc_3)
        into.read(i + into_offset, tmp_bf_0)
        gc_iter(i)

    return into


def cross_inner_product(l0, r0, l1, r1):
    """
    t1_1 = l0 . r1,     t1_2 = l1 . r0
    t1   = t1_1 + t1_2, t2   = l1 . r1
    """
    sc_t1_1, sc_t1_2, sc_t2 = alloc_scalars(3)
    cl0, cr0, cl1, cr1 = alloc_scalars(4)

    for i in range(len(l0)):
        crypto.decodeint_into_noreduce(cl0, l0.to(i))
        crypto.decodeint_into_noreduce(cr0, r0.to(i))
        crypto.decodeint_into_noreduce(cl1, l1.to(i))
        crypto.decodeint_into_noreduce(cr1, r1.to(i))

        crypto.sc_muladd_into(sc_t1_1, cl0, cr1, sc_t1_1)
        crypto.sc_muladd_into(sc_t1_2, cl1, cr0, sc_t1_2)
        crypto.sc_muladd_into(sc_t2, cl1, cr1, sc_t2)
        gc_iter(i)

    crypto.sc_add_into(sc_t1_1, sc_t1_1, sc_t1_2)
    return crypto.encodeint(sc_t1_1), crypto.encodeint(sc_t2)


def vector_gen(dst, size, op):
    dst = _ensure_dst_keyvect(dst, size)
    for i in range(size):
        dst.to(i, tmp_bf_0)
        op(i, tmp_bf_0)
        dst.read(i, tmp_bf_0)
        gc_iter(i)
    return dst


def vector_add(a, b, dst=None):
    dst = _ensure_dst_keyvect(dst, len(a))
    for i in range(len(a)):
        sc_add(tmp_bf_1, a.to(i), b.to(i))
        dst.read(i, tmp_bf_1)
        gc_iter(i)
    return dst


def vector_subtract(a, b, dst=None):
    dst = _ensure_dst_keyvect(dst, len(a))
    for i in range(len(a)):
        sc_sub(tmp_bf_1, a.to(i), b.to(i))
        dst.read(i, tmp_bf_1)
        gc_iter(i)
    return dst


def vector_dup(x, n, dst=None):
    dst = _ensure_dst_keyvect(dst, n)
    for i in range(n):
        dst[i] = x
        gc_iter(i)
    return dst


def vector_z_two_i(logN, zpow, twoN, i, dst_sc=None):
    """
    0...N|N+1...2N|2N+1...3N|....
    zt[i] = z^b 2^c, where
      b = 2 + blockNumber. BlockNumber is idx of N block
      c = i % N = i - N * blockNumber
    """
    j = i >> logN
    crypto.decodeint_into_noreduce(tmp_sc_1, zpow.to(j + 2))
    crypto.decodeint_into_noreduce(tmp_sc_2, twoN.to(i & ((1 << logN) - 1)))
    crypto.sc_mul_into(dst_sc, tmp_sc_1, tmp_sc_2)
    return dst_sc


def vector_z_two(N, logN, M, zpow, twoN, zero_twos=None, dynamic=False, **kwargs):
    if dynamic:
        return KeyVZtwo(N, logN, M, zpow, twoN, **kwargs)
    else:
        raise NotImplementedError


def hash_cache_mash(dst, hash_cache, *args):
    dst = _ensure_dst_key(dst)
    ctx = crypto.get_keccak()
    ctx.update(hash_cache)

    for x in args:
        if x is None:
            break
        ctx.update(x)
    hsh = ctx.digest()

    crypto.decodeint_into(tmp_sc_1, hsh)
    crypto.encodeint_into(tmp_bf_1, tmp_sc_1)

    copy_key(dst, tmp_bf_1)
    copy_key(hash_cache, tmp_bf_1)
    return dst


def is_reduced(sc):
    return crypto.encodeint(crypto.decodeint(sc)) == sc


class MultiExpSequential:
    """
    MultiExp object similar to MultiExp array of [(scalar, point), ]
    MultiExp computes simply: res = \\sum_i scalar_i * point_i
    Straus / Pippenger algorithms are implemented in the original Monero C++ code for the speed
    but the memory cost is around 1 MB which is not affordable here in HW devices.

    Moreover, Monero needs speed for very fast verification for blockchain verification which is not
    priority in this use case.

    MultiExp holder with sequential evaluation
    """

    def __init__(self, size=None, points=None, point_fnc=None):
        self.current_idx = 0
        self.size = size if size else None
        self.points = points if points else []
        self.point_fnc = point_fnc
        if points and size is None:
            self.size = len(points) if points else 0
        else:
            self.size = 0

        self.acc = crypto.identity()
        self.tmp = _ensure_dst_key()

    def get_point(self, idx):
        return (
            self.point_fnc(idx, None) if idx >= len(self.points) else self.points[idx]
        )

    def add_pair(self, scalar, point):
        self._acc(scalar, point)

    def add_scalar(self, scalar):
        self._acc(scalar, self.get_point(self.current_idx))

    def _acc(self, scalar, point):
        crypto.decodeint_into_noreduce(tmp_sc_1, scalar)
        crypto.decodepoint_into(tmp_pt_2, point)
        crypto.scalarmult_into(tmp_pt_3, tmp_pt_2, tmp_sc_1)
        crypto.point_add_into(self.acc, self.acc, tmp_pt_3)
        self.current_idx += 1
        self.size += 1

    def eval(self, dst, GiHi=False):
        dst = _ensure_dst_key(dst)
        return crypto.encodepoint_into(dst, self.acc)


def multiexp(dst=None, data=None, GiHi=False):
    return data.eval(dst, GiHi)


class BulletProofBuilder:
    def __init__(self):
        self.use_det_masks = True
        self.proof_sec = None

        self.Gprec = KeyV(buffer=BP_GI_PRE, const=True)
        self.Hprec = KeyV(buffer=BP_HI_PRE, const=True)
        self.oneN = const_vector(ONE, 64)
        self.twoN = KeyV(buffer=BP_TWO_N, const=True)
        self.ip12 = BP_IP12
        self.fnc_det_mask = None

        self.tmp_sc_1 = crypto.new_scalar()
        self.tmp_det_buff = bytearray(64 + 1 + 4)

        self.gc_fnc = gc.collect
        self.gc_trace = None

    def gc(self, *args):
        if self.gc_trace:
            self.gc_trace(*args)
        if self.gc_fnc:
            self.gc_fnc()

    def aX_vcts(self, sv, MN):
        num_inp = len(sv)

        def e_xL(idx, d=None, is_a=True):
            j, i = idx // BP_N, idx % BP_N
            r = None
            if j >= num_inp:
                r = ZERO if is_a else MINUS_ONE
            elif sv[j][i // 8] & (1 << i % 8):
                r = ONE if is_a else ZERO
            else:
                r = ZERO if is_a else MINUS_ONE
            if d:
                memcpy(d, 0, r, 0, 32)
            return r

        aL = KeyVEval(MN, lambda i, d: e_xL(i, d, True))
        aR = KeyVEval(MN, lambda i, d: e_xL(i, d, False))
        return aL, aR

    def _det_mask_init(self):
        memcpy(self.tmp_det_buff, 0, self.proof_sec, 0, len(self.proof_sec))

    def _det_mask(self, i, is_sL=True, dst=None):
        dst = _ensure_dst_key(dst)
        if self.fnc_det_mask:
            return self.fnc_det_mask(i, is_sL, dst)
        self.tmp_det_buff[64] = int(is_sL)
        memcpy(self.tmp_det_buff, 65, ZERO, 0, 4)
        dump_uvarint_b_into(i, self.tmp_det_buff, 65)
        crypto.hash_to_scalar_into(self.tmp_sc_1, self.tmp_det_buff)
        crypto.encodeint_into(dst, self.tmp_sc_1)
        return dst

    def _gprec_aux(self, size):
        return KeyVPrecomp(
            size, self.Gprec, lambda i, d: get_exponent(d, XMR_H, i * 2 + 1)
        )

    def _hprec_aux(self, size):
        return KeyVPrecomp(size, self.Hprec, lambda i, d: get_exponent(d, XMR_H, i * 2))

    def _two_aux(self, size):
        # Simple recursive exponentiation from precomputed results
        lx = len(self.twoN)

        def pow_two(i, d=None):
            if i < lx:
                return self.twoN[i]

            d = _ensure_dst_key(d)
            flr = i // 2

            lw = pow_two(flr)
            rw = pow_two(flr + 1 if flr != i / 2.0 else lw)
            return sc_mul(d, lw, rw)

        return KeyVPrecomp(size, self.twoN, pow_two)

    def sL_vct(self, ln=BP_N):
        return (
            KeyVEval(ln, lambda i, dst: self._det_mask(i, True, dst))
            if self.use_det_masks
            else self.sX_gen(ln)
        )

    def sR_vct(self, ln=BP_N):
        return (
            KeyVEval(ln, lambda i, dst: self._det_mask(i, False, dst))
            if self.use_det_masks
            else self.sX_gen(ln)
        )

    def sX_gen(self, ln=BP_N):
        gc.collect()
        buff = bytearray(ln * 32)
        buff_mv = memoryview(buff)
        sc = crypto.new_scalar()
        for i in range(ln):
            crypto.random_scalar(sc)
            crypto.encodeint_into(buff_mv[i * 32 : (i + 1) * 32], sc)
            gc_iter(i)
        return KeyV(buffer=buff)

    def vector_exponent(self, a, b, dst=None):
        return vector_exponent_custom(self.Gprec, self.Hprec, a, b, dst)

    def prove_testnet(self, sv, gamma):
        return self.prove(sv, gamma, proof_v8=True)

    def prove(self, sv, gamma, proof_v8=False):
        return self.prove_batch([sv], [gamma], proof_v8=proof_v8)

    def prove_setup(self, sv, gamma, proof_v8=False):
        utils.ensure(len(sv) == len(gamma), "|sv| != |gamma|")
        utils.ensure(len(sv) > 0, "sv empty")

        self.proof_sec = crypto.random_bytes(64)
        self._det_mask_init()
        gc.collect()
        sv = [crypto.encodeint(x) for x in sv]
        gamma = [crypto.encodeint(x) for x in gamma]

        M, logM = 1, 0
        while M <= BP_M and M < len(sv):
            logM += 1
            M = 1 << logM
        MN = M * BP_N

        V = _ensure_dst_keyvect(None, len(sv))
        for i in range(len(sv)):
            add_keys2(tmp_bf_0, gamma[i], sv[i], XMR_H)
            if not proof_v8:
                scalarmult_key(tmp_bf_0, tmp_bf_0, INV_EIGHT)
            V.read(i, tmp_bf_0)

        aL, aR = self.aX_vcts(sv, MN)
        return M, logM, aL, aR, V, gamma

    def prove_batch(self, sv, gamma, proof_v8=False):
        M, logM, aL, aR, V, gamma = self.prove_setup(sv, gamma, proof_v8)
        hash_cache = _ensure_dst_key()
        while True:
            self.gc(10)
            r = self._prove_batch_main(
                V, gamma, aL, aR, hash_cache, logM, BP_LOG_N, M, BP_N, proof_v8
            )
            if r[0]:
                break
        return r[1]

    def _prove_batch_main(
        self, V, gamma, aL, aR, hash_cache, logM, logN, M, N, proof_v8=False
    ):
        logMN = logM + logN
        MN = M * N
        hash_vct_to_scalar(hash_cache, V)

        # Extended precomputed GiHi
        Gprec = self._gprec_aux(MN)
        Hprec = self._hprec_aux(MN)

        # PAPER LINES 38-39
        alpha = sc_gen()
        ve = _ensure_dst_key()
        A = _ensure_dst_key()
        vector_exponent_custom(Gprec, Hprec, aL, aR, ve)
        add_keys(A, ve, scalarmult_base(tmp_bf_1, alpha))
        if not proof_v8:
            scalarmult_key(A, A, INV_EIGHT)
        self.gc(11)

        # PAPER LINES 40-42
        sL = self.sL_vct(MN)
        sR = self.sR_vct(MN)
        rho = sc_gen()
        vector_exponent_custom(Gprec, Hprec, sL, sR, ve)
        S = _ensure_dst_key()
        add_keys(S, ve, scalarmult_base(tmp_bf_1, rho))
        if not proof_v8:
            scalarmult_key(S, S, INV_EIGHT)
        del ve
        self.gc(12)

        # PAPER LINES 43-45
        y = _ensure_dst_key()
        hash_cache_mash(y, hash_cache, A, S)
        if y == ZERO:
            return (0,)

        z = _ensure_dst_key()
        hash_to_scalar(hash_cache, y)
        copy_key(z, hash_cache)
        if z == ZERO:
            return (0,)

        # Polynomial construction by coefficients
        zMN = const_vector(z, MN)
        l0 = _ensure_dst_keyvect(None, MN)
        vector_subtract(aL, zMN, l0)
        l1 = sL
        self.gc(13)

        # This computes the ugly sum/concatenation from PAPER LINE 65
        # r0 = aR + z
        r0 = vector_add(aR, zMN)
        del zMN
        self.gc(14)

        # r0 = r0 \odot yMN => r0[i]  = r0[i] * y^i
        # r1 = sR \odot yMN => r1[i]  = sR[i] * y^i
        yMN = vector_powers(y, MN, dynamic=False)
        hadamard(r0, yMN, dst=r0)
        self.gc(15)

        # r0 = r0 + zero_twos
        zpow = vector_powers(z, M + 2)
        twoN = self._two_aux(MN)
        zero_twos = vector_z_two(N, logN, M, zpow, twoN, dynamic=True, raw=True)
        vector_gen(
            r0,
            len(r0),
            lambda i, d: crypto.encodeint_into(
                d,
                crypto.sc_add_into(
                    tmp_sc_1,
                    zero_twos[i],  # noqa: F821
                    crypto.decodeint_into_noreduce(tmp_sc_2, r0.to(i)),  # noqa: F821
                ),
            ),
        )

        del (zero_twos, twoN)
        self.gc(15)

        # Polynomial construction before PAPER LINE 46
        # r1 = KeyVEval(MN, lambda i, d: sc_mul(d, yMN[i], sR[i]))
        # r1 optimization possible, but has clashing sc registers.
        # Moreover, max memory complexity is 4MN as below (while loop).
        r1 = hadamard(yMN, sR, yMN)  # re-use yMN vector for r1
        del (yMN, sR)
        self.gc(16)

        # Inner products
        # l0 = aL - z           r0   = ((aR + z) \cdot ypow) + zt
        # l1 = sL               r1   =   sR      \cdot ypow
        # t1_1 = l0 . r1,       t1_2 = l1 . r0
        # t1   = t1_1 + t1_2,   t2   = l1 . r1
        # l = l0 \odot x*l1     r    = r0 \odot x*r1
        t1, t2 = cross_inner_product(l0, r0, l1, r1)
        self.gc(17)

        # PAPER LINES 47-48
        tau1, tau2 = sc_gen(), sc_gen()
        T1, T2 = _ensure_dst_key(), _ensure_dst_key()

        add_keys(T1, scalarmultH(tmp_bf_1, t1), scalarmult_base(tmp_bf_2, tau1))
        if not proof_v8:
            scalarmult_key(T1, T1, INV_EIGHT)

        add_keys(T2, scalarmultH(tmp_bf_1, t2), scalarmult_base(tmp_bf_2, tau2))
        if not proof_v8:
            scalarmult_key(T2, T2, INV_EIGHT)
        del (t1, t2)
        self.gc(17)

        # PAPER LINES 49-51
        x = _ensure_dst_key()
        hash_cache_mash(x, hash_cache, z, T1, T2)
        if x == ZERO:
            return (0,)

        # PAPER LINES 52-53
        taux = _ensure_dst_key()
        copy_key(taux, ZERO)
        sc_mul(taux, tau1, x)
        xsq = _ensure_dst_key()
        sc_mul(xsq, x, x)
        sc_muladd(taux, tau2, xsq, taux)
        del (xsq, tau1, tau2)
        for j in range(1, len(V) + 1):
            sc_muladd(taux, zpow.to(j + 1), gamma[j - 1], taux)
        del zpow

        self.gc(18)
        mu = _ensure_dst_key()
        sc_muladd(mu, x, rho, alpha)
        del (rho, alpha)

        # PAPER LINES 54-57
        # l = l0 \odot x*l1, has to evaluated as it becomes aprime in the loop
        l = vector_gen(
            l0,
            len(l0),
            lambda i, d: sc_add(d, d, sc_mul(tmp_bf_1, l1.to(i), x)),  # noqa: F821
        )
        del (l0, l1, sL)
        self.gc(19)

        # r = r0 \odot x*r1, has to evaluated as it becomes bprime in the loop
        r = vector_gen(
            r0,
            len(r0),
            lambda i, d: sc_add(d, d, sc_mul(tmp_bf_1, r1.to(i), x)),  # noqa: F821
        )
        t = inner_product(l, r)
        del (r1, r0)
        self.gc(19)

        # PAPER LINES 32-33
        x_ip = hash_cache_mash(None, hash_cache, x, taux, mu, t)
        if x_ip == ZERO:
            return 0, None

        # PHASE 2
        # These are used in the inner product rounds
        nprime = MN
        Gprime = _ensure_dst_keyvect(None, MN)
        Hprime = _ensure_dst_keyvect(None, MN)
        aprime = l
        bprime = r
        yinv = invert(None, y)
        yinvpow = init_key(ONE)
        self.gc(20)

        for i in range(0, MN):
            Gprime.read(i, Gprec.to(i))
            scalarmult_key(tmp_bf_0, Hprec.to(i), yinvpow)
            Hprime.read(i, tmp_bf_0)
            sc_mul(yinvpow, yinvpow, yinv)
            gc_iter(i)
        self.gc(21)

        L = _ensure_dst_keyvect(None, logMN)
        R = _ensure_dst_keyvect(None, logMN)
        cL = _ensure_dst_key()
        cR = _ensure_dst_key()
        winv = _ensure_dst_key()
        w_round = _ensure_dst_key()
        tmp = _ensure_dst_key()

        round = 0
        _tmp_k_1 = _ensure_dst_key()

        # PAPER LINE 13
        while nprime > 1:
            # PAPER LINE 15
            npr2 = nprime
            nprime >>= 1
            self.gc(22)

            # PAPER LINES 16-17
            inner_product(
                aprime.slice_view(0, nprime), bprime.slice_view(nprime, npr2), cL
            )

            inner_product(
                aprime.slice_view(nprime, npr2), bprime.slice_view(0, nprime), cR
            )
            self.gc(23)

            # PAPER LINES 18-19
            vector_exponent_custom(
                Gprime.slice_view(nprime, npr2),
                Hprime.slice_view(0, nprime),
                aprime.slice_view(0, nprime),
                bprime.slice_view(nprime, npr2),
                tmp_bf_0,
            )

            sc_mul(tmp, cL, x_ip)
            add_keys(tmp_bf_0, tmp_bf_0, scalarmultH(_tmp_k_1, tmp))
            if not proof_v8:
                scalarmult_key(tmp_bf_0, tmp_bf_0, INV_EIGHT)
            L.read(round, tmp_bf_0)
            self.gc(24)

            vector_exponent_custom(
                Gprime.slice_view(0, nprime),
                Hprime.slice_view(nprime, npr2),
                aprime.slice_view(nprime, npr2),
                bprime.slice_view(0, nprime),
                tmp_bf_0,
            )

            sc_mul(tmp, cR, x_ip)
            add_keys(tmp_bf_0, tmp_bf_0, scalarmultH(_tmp_k_1, tmp))
            if not proof_v8:
                scalarmult_key(tmp_bf_0, tmp_bf_0, INV_EIGHT)
            R.read(round, tmp_bf_0)
            self.gc(25)

            # PAPER LINES 21-22
            hash_cache_mash(w_round, hash_cache, L.to(round), R.to(round))
            if w_round == ZERO:
                return (0,)

            # PAPER LINES 24-25
            invert(winv, w_round)
            self.gc(26)

            hadamard_fold(Gprime, winv, w_round)
            self.gc(27)

            hadamard_fold(Hprime, w_round, winv, Gprime, nprime)
            Hprime.realloc_init_from(nprime, Gprime, nprime, round < 2)
            self.gc(28)

            # PAPER LINES 28-29
            scalar_fold(aprime, w_round, winv, Gprime, nprime)
            aprime.realloc_init_from(nprime, Gprime, nprime, round < 2)
            self.gc(29)

            scalar_fold(bprime, winv, w_round, Gprime, nprime)
            bprime.realloc_init_from(nprime, Gprime, nprime, round < 2)
            self.gc(30)

            # Finally resize Gprime which was buffer for all ops
            Gprime.resize(nprime, realloc=True)
            round += 1

        from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import Bulletproof

        return (
            1,
            Bulletproof(
                V=V,
                A=A,
                S=S,
                T1=T1,
                T2=T2,
                taux=taux,
                mu=mu,
                L=L,
                R=R,
                a=aprime.to(0),
                b=bprime.to(0),
                t=t,
            ),
        )

    def verify_testnet(self, proof):
        return self.verify(proof, proof_v8=True)

    def verify(self, proof, proof_v8=False):
        return self.verify_batch([proof], proof_v8=proof_v8)

    def verify_batch(self, proofs, single_optim=True, proof_v8=False):
        """
        BP batch verification
        :param proofs:
        :param single_optim: single proof memory optimization
        :param proof_v8: previous testnet version
        :return:
        """
        max_length = 0
        for proof in proofs:
            utils.ensure(is_reduced(proof.taux), "Input scalar not in range")
            utils.ensure(is_reduced(proof.mu), "Input scalar not in range")
            utils.ensure(is_reduced(proof.a), "Input scalar not in range")
            utils.ensure(is_reduced(proof.b), "Input scalar not in range")
            utils.ensure(is_reduced(proof.t), "Input scalar not in range")
            utils.ensure(len(proof.V) >= 1, "V does not have at least one element")
            utils.ensure(len(proof.L) == len(proof.R), "|L| != |R|")
            utils.ensure(len(proof.L) > 0, "Empty proof")
            max_length = max(max_length, len(proof.L))

        utils.ensure(max_length < 32, "At least one proof is too large")

        maxMN = 1 << max_length
        logN = 6
        N = 1 << logN
        tmp = _ensure_dst_key()

        # setup weighted aggregates
        is_single = len(proofs) == 1 and single_optim  # ph4
        z1 = init_key(ZERO)
        z3 = init_key(ZERO)
        m_z4 = vector_dup(ZERO, maxMN) if not is_single else None
        m_z5 = vector_dup(ZERO, maxMN) if not is_single else None
        m_y0 = init_key(ZERO)
        y1 = init_key(ZERO)
        muex_acc = init_key(ONE)

        Gprec = self._gprec_aux(maxMN)
        Hprec = self._hprec_aux(maxMN)

        for proof in proofs:
            M = 1
            logM = 0
            while M <= BP_M and M < len(proof.V):
                logM += 1
                M = 1 << logM

            utils.ensure(len(proof.L) == 6 + logM, "Proof is not the expected size")
            MN = M * N
            weight_y = crypto.encodeint(crypto.random_scalar())
            weight_z = crypto.encodeint(crypto.random_scalar())

            # Reconstruct the challenges
            hash_cache = hash_vct_to_scalar(None, proof.V)
            y = hash_cache_mash(None, hash_cache, proof.A, proof.S)
            utils.ensure(y != ZERO, "y == 0")
            z = hash_to_scalar(None, y)
            copy_key(hash_cache, z)
            utils.ensure(z != ZERO, "z == 0")

            x = hash_cache_mash(None, hash_cache, z, proof.T1, proof.T2)
            utils.ensure(x != ZERO, "x == 0")
            x_ip = hash_cache_mash(None, hash_cache, x, proof.taux, proof.mu, proof.t)
            utils.ensure(x_ip != ZERO, "x_ip == 0")

            # PAPER LINE 61
            sc_mulsub(m_y0, proof.taux, weight_y, m_y0)
            zpow = vector_powers(z, M + 3)

            k = _ensure_dst_key()
            ip1y = vector_power_sum(y, MN)
            sc_mulsub(k, zpow[2], ip1y, ZERO)
            for j in range(1, M + 1):
                utils.ensure(j + 2 < len(zpow), "invalid zpow index")
                sc_mulsub(k, zpow.to(j + 2), BP_IP12, k)

            # VERIFY_line_61rl_new
            sc_muladd(tmp, z, ip1y, k)
            sc_sub(tmp, proof.t, tmp)

            sc_muladd(y1, tmp, weight_y, y1)
            weight_y8 = init_key(weight_y)
            if not proof_v8:
                weight_y8 = sc_mul(None, weight_y, EIGHT)

            muex = MultiExpSequential(points=[pt for pt in proof.V])
            for j in range(len(proof.V)):
                sc_mul(tmp, zpow[j + 2], weight_y8)
                muex.add_scalar(init_key(tmp))

            sc_mul(tmp, x, weight_y8)
            muex.add_pair(init_key(tmp), proof.T1)

            xsq = _ensure_dst_key()
            sc_mul(xsq, x, x)

            sc_mul(tmp, xsq, weight_y8)
            muex.add_pair(init_key(tmp), proof.T2)

            weight_z8 = init_key(weight_z)
            if not proof_v8:
                weight_z8 = sc_mul(None, weight_z, EIGHT)

            muex.add_pair(weight_z8, proof.A)
            sc_mul(tmp, x, weight_z8)
            muex.add_pair(init_key(tmp), proof.S)

            multiexp(tmp, muex, False)
            add_keys(muex_acc, muex_acc, tmp)
            del muex

            # Compute the number of rounds for the inner product
            rounds = logM + logN
            utils.ensure(rounds > 0, "Zero rounds")

            # PAPER LINES 21-22
            # The inner product challenges are computed per round
            w = _ensure_dst_keyvect(None, rounds)
            for i in range(rounds):
                hash_cache_mash(tmp_bf_0, hash_cache, proof.L[i], proof.R[i])
                w.read(i, tmp_bf_0)
                utils.ensure(w[i] != ZERO, "w[i] == 0")

            # Basically PAPER LINES 24-25
            # Compute the curvepoints from G[i] and H[i]
            yinvpow = init_key(ONE)
            ypow = init_key(ONE)
            yinv = invert(None, y)
            self.gc(61)

            winv = _ensure_dst_keyvect(None, rounds)
            for i in range(rounds):
                invert(tmp_bf_0, w.to(i))
                winv.read(i, tmp_bf_0)
                self.gc(62)

            g_scalar = _ensure_dst_key()
            h_scalar = _ensure_dst_key()
            twoN = self._two_aux(N)
            for i in range(MN):
                copy_key(g_scalar, proof.a)
                sc_mul(h_scalar, proof.b, yinvpow)

                for j in range(rounds - 1, -1, -1):
                    J = len(w) - j - 1

                    if (i & (1 << j)) == 0:
                        sc_mul(g_scalar, g_scalar, winv.to(J))
                        sc_mul(h_scalar, h_scalar, w.to(J))
                    else:
                        sc_mul(g_scalar, g_scalar, w.to(J))
                        sc_mul(h_scalar, h_scalar, winv.to(J))

                # Adjust the scalars using the exponents from PAPER LINE 62
                sc_add(g_scalar, g_scalar, z)
                utils.ensure(2 + i // N < len(zpow), "invalid zpow index")
                utils.ensure(i % N < len(twoN), "invalid twoN index")
                sc_mul(tmp, zpow.to(2 + i // N), twoN.to(i % N))
                sc_muladd(tmp, z, ypow, tmp)
                sc_mulsub(h_scalar, tmp, yinvpow, h_scalar)

                if not is_single:  # ph4
                    sc_mulsub(m_z4[i], g_scalar, weight_z, m_z4[i])
                    sc_mulsub(m_z5[i], h_scalar, weight_z, m_z5[i])
                else:
                    sc_mul(tmp, g_scalar, weight_z)
                    sub_keys(muex_acc, muex_acc, scalarmult_key(tmp, Gprec.to(i), tmp))

                    sc_mul(tmp, h_scalar, weight_z)
                    sub_keys(muex_acc, muex_acc, scalarmult_key(tmp, Hprec.to(i), tmp))

                if i != MN - 1:
                    sc_mul(yinvpow, yinvpow, yinv)
                    sc_mul(ypow, ypow, y)
                if i & 15 == 0:
                    self.gc(62)

            del (g_scalar, h_scalar, twoN)
            self.gc(63)

            sc_muladd(z1, proof.mu, weight_z, z1)
            muex = MultiExpSequential(
                point_fnc=lambda i, d: proof.L[i // 2]
                if i & 1 == 0
                else proof.R[i // 2]
            )
            for i in range(rounds):
                sc_mul(tmp, w[i], w[i])
                sc_mul(tmp, tmp, weight_z8)
                muex.add_scalar(tmp)
                sc_mul(tmp, winv[i], winv[i])
                sc_mul(tmp, tmp, weight_z8)
                muex.add_scalar(tmp)

            acc = multiexp(None, muex, False)
            add_keys(muex_acc, muex_acc, acc)

            sc_mulsub(tmp, proof.a, proof.b, proof.t)
            sc_mul(tmp, tmp, x_ip)
            sc_muladd(z3, tmp, weight_z, z3)

        sc_sub(tmp, m_y0, z1)
        z3p = sc_sub(None, z3, y1)

        check2 = crypto.encodepoint(
            crypto.ge25519_double_scalarmult_base_vartime(
                crypto.decodeint(z3p), crypto.xmr_H(), crypto.decodeint(tmp)
            )
        )
        add_keys(muex_acc, muex_acc, check2)

        if not is_single:  # ph4
            muex = MultiExpSequential(
                point_fnc=lambda i, d: Gprec.to(i // 2)
                if i & 1 == 0
                else Hprec.to(i // 2)
            )
            for i in range(maxMN):
                muex.add_scalar(m_z4[i])
                muex.add_scalar(m_z5[i])
            add_keys(muex_acc, muex_acc, multiexp(None, muex, True))

        if muex_acc != ONE:
            raise ValueError("Verification failure at step 2")
        return True
