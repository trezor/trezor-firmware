import gc
from micropython import const

from trezor import utils
from trezor.utils import memcpy as tmemcpy

from apps.monero.xmr import crypto
from apps.monero.xmr.serialize.int_serialize import dump_uvarint_b_into, uvarint_size

# Constants

_BP_LOG_N = const(6)
_BP_N = const(64)  # 1 << _BP_LOG_N
_BP_M = const(16)  # maximal number of bulletproofs

_ZERO = b"\x00" * 32
_ONE = b"\x01" + b"\x00" * 31
_TWO = b"\x02" + b"\x00" * 31
_EIGHT = b"\x08" + b"\x00" * 31
_INV_EIGHT = crypto.INV_EIGHT
_MINUS_ONE = b"\xec\xd3\xf5\x5c\x1a\x63\x12\x58\xd6\x9c\xf7\xa2\xde\xf9\xde\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10"
# _MINUS_INV_EIGHT = b"\x74\xa4\x19\x7a\xf0\x7d\x0b\xf7\x05\xc2\xda\x25\x2b\x5c\x0b\x0d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0a"

# Monero H point
_XMR_H = b"\x8b\x65\x59\x70\x15\x37\x99\xaf\x2a\xea\xdc\x9f\xf1\xad\xd0\xea\x6c\x72\x51\xd5\x41\x54\xcf\xa9\x2c\x17\x3a\x0d\xd3\x9c\x1f\x94"
_XMR_HP = crypto.xmr_H()

# ip12 = inner_product(oneN, twoN);
_BP_IP12 = b"\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"


#
# Rct keys operations
# tmp_x are global working registers to minimize memory allocations / heap fragmentation.
# Caution has to be exercised when using the registers and operations using the registers
#

_tmp_bf_0 = bytearray(32)
_tmp_bf_1 = bytearray(32)
_tmp_bf_2 = bytearray(32)
_tmp_bf_exp = bytearray(11 + 32 + 4)

_tmp_pt_1 = crypto.new_point()
_tmp_pt_2 = crypto.new_point()
_tmp_pt_3 = crypto.new_point()
_tmp_pt_4 = crypto.new_point()

_tmp_sc_1 = crypto.new_scalar()
_tmp_sc_2 = crypto.new_scalar()
_tmp_sc_3 = crypto.new_scalar()
_tmp_sc_4 = crypto.new_scalar()


def _ensure_dst_key(dst=None):
    if dst is None:
        dst = bytearray(32)
    return dst


def memcpy(dst, dst_off, src, src_off, len):
    if dst is not None:
        tmemcpy(dst, dst_off, src, src_off, len)
    return dst


def _alloc_scalars(num=1):
    return (crypto.new_scalar() for _ in range(num))


def _copy_key(dst, src):
    for i in range(32):
        dst[i] = src[i]
    return dst


def _init_key(val, dst=None):
    dst = _ensure_dst_key(dst)
    return _copy_key(dst, val)


def _gc_iter(i):
    if i & 127 == 0:
        gc.collect()


def _invert(dst, x):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(_tmp_sc_1, x)
    crypto.sc_inv_into(_tmp_sc_2, _tmp_sc_1)
    crypto.encodeint_into(dst, _tmp_sc_2)
    return dst


def _scalarmult_key(dst, P, s, s_raw=None, tmp_pt=_tmp_pt_1):
    dst = _ensure_dst_key(dst)
    crypto.decodepoint_into(tmp_pt, P)
    if s:
        crypto.decodeint_into_noreduce(_tmp_sc_1, s)
    crypto.scalarmult_into(tmp_pt, tmp_pt, _tmp_sc_1 if s else s_raw)
    crypto.encodepoint_into(dst, tmp_pt)
    return dst


def _scalarmultH(dst, x):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into(_tmp_sc_1, x)
    crypto.scalarmult_into(_tmp_pt_1, _XMR_HP, _tmp_sc_1)
    crypto.encodepoint_into(dst, _tmp_pt_1)
    return dst


def _scalarmult_base(dst, x):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(_tmp_sc_1, x)
    crypto.scalarmult_base_into(_tmp_pt_1, _tmp_sc_1)
    crypto.encodepoint_into(dst, _tmp_pt_1)
    return dst


def _sc_gen(dst=None):
    dst = _ensure_dst_key(dst)
    crypto.random_scalar(_tmp_sc_1)
    crypto.encodeint_into(dst, _tmp_sc_1)
    return dst


def _sc_add(dst, a, b):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    crypto.decodeint_into_noreduce(_tmp_sc_2, b)
    crypto.sc_add_into(_tmp_sc_3, _tmp_sc_1, _tmp_sc_2)
    crypto.encodeint_into(dst, _tmp_sc_3)
    return dst


def _sc_sub(dst, a, b, a_raw=None, b_raw=None):
    dst = _ensure_dst_key(dst)
    if a:
        crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    if b:
        crypto.decodeint_into_noreduce(_tmp_sc_2, b)
    crypto.sc_sub_into(_tmp_sc_3, _tmp_sc_1 if a else a_raw, _tmp_sc_2 if b else b_raw)
    crypto.encodeint_into(dst, _tmp_sc_3)
    return dst


def _sc_mul(dst, a, b=None, b_raw=None):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    if b:
        crypto.decodeint_into_noreduce(_tmp_sc_2, b)
    crypto.sc_mul_into(_tmp_sc_3, _tmp_sc_1, _tmp_sc_2 if b else b_raw)
    crypto.encodeint_into(dst, _tmp_sc_3)
    return dst


def _sc_muladd(dst, a, b, c, a_raw=None, b_raw=None, c_raw=None, raw=False):
    dst = _ensure_dst_key(dst) if not raw else (dst if dst else crypto.new_scalar())
    if a:
        crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    if b:
        crypto.decodeint_into_noreduce(_tmp_sc_2, b)
    if c:
        crypto.decodeint_into_noreduce(_tmp_sc_3, c)
    crypto.sc_muladd_into(
        _tmp_sc_4 if not raw else dst,
        _tmp_sc_1 if a else a_raw,
        _tmp_sc_2 if b else b_raw,
        _tmp_sc_3 if c else c_raw,
    )
    if not raw:
        crypto.encodeint_into(dst, _tmp_sc_4)
    return dst


def _sc_mulsub(dst, a, b, c):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    crypto.decodeint_into_noreduce(_tmp_sc_2, b)
    crypto.decodeint_into_noreduce(_tmp_sc_3, c)
    crypto.sc_mulsub_into(_tmp_sc_4, _tmp_sc_1, _tmp_sc_2, _tmp_sc_3)
    crypto.encodeint_into(dst, _tmp_sc_4)
    return dst


def _add_keys(dst, A, B):
    dst = _ensure_dst_key(dst)
    crypto.decodepoint_into(_tmp_pt_1, A)
    crypto.decodepoint_into(_tmp_pt_2, B)
    crypto.point_add_into(_tmp_pt_3, _tmp_pt_1, _tmp_pt_2)
    crypto.encodepoint_into(dst, _tmp_pt_3)
    return dst


def _sub_keys(dst, A, B):
    dst = _ensure_dst_key(dst)
    crypto.decodepoint_into(_tmp_pt_1, A)
    crypto.decodepoint_into(_tmp_pt_2, B)
    crypto.point_sub_into(_tmp_pt_3, _tmp_pt_1, _tmp_pt_2)
    crypto.encodepoint_into(dst, _tmp_pt_3)
    return dst


def _add_keys2(dst, a, b, B):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    crypto.decodeint_into_noreduce(_tmp_sc_2, b)
    crypto.decodepoint_into(_tmp_pt_1, B)
    crypto.add_keys2_into(_tmp_pt_2, _tmp_sc_1, _tmp_sc_2, _tmp_pt_1)
    crypto.encodepoint_into(dst, _tmp_pt_2)
    return dst


def _add_keys3(dst, a, A, b, B):
    dst = _ensure_dst_key(dst)
    crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    crypto.decodeint_into_noreduce(_tmp_sc_2, b)
    crypto.decodepoint_into(_tmp_pt_1, A)
    crypto.decodepoint_into(_tmp_pt_2, B)
    crypto.add_keys3_into(_tmp_pt_3, _tmp_sc_1, _tmp_pt_1, _tmp_sc_2, _tmp_pt_2)
    crypto.encodepoint_into(dst, _tmp_pt_3)
    return dst


def _hash_to_scalar(dst, data):
    dst = _ensure_dst_key(dst)
    crypto.hash_to_scalar_into(_tmp_sc_1, data)
    crypto.encodeint_into(dst, _tmp_sc_1)
    return dst


def _hash_vct_to_scalar(dst, data):
    dst = _ensure_dst_key(dst)
    ctx = crypto.get_keccak()
    for x in data:
        ctx.update(x)
    hsh = ctx.digest()

    crypto.decodeint_into(_tmp_sc_1, hsh)
    crypto.encodeint_into(dst, _tmp_sc_1)
    return dst


def _get_exponent(dst, base, idx):
    dst = _ensure_dst_key(dst)
    salt = b"bulletproof"
    lsalt = const(11)  # len(salt)
    final_size = lsalt + 32 + uvarint_size(idx)
    memcpy(_tmp_bf_exp, 0, base, 0, 32)
    memcpy(_tmp_bf_exp, 32, salt, 0, lsalt)
    dump_uvarint_b_into(idx, _tmp_bf_exp, 32 + lsalt)
    crypto.keccak_hash_into(_tmp_bf_1, _tmp_bf_exp, final_size)
    crypto.hash_to_point_into(_tmp_pt_4, _tmp_bf_1)
    crypto.encodepoint_into(dst, _tmp_pt_4)
    return dst


#
# Key Vectors
#


class KeyVBase:
    """
    Base KeyVector object
    """

    __slots__ = ("current_idx", "size")

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

    def to(self, idx, buff=None, offset=0):
        buff = _ensure_dst_key(buff)
        return memcpy(buff, offset, self.to(self.idxize(idx)), 0, 32)

    def read(self, idx, buff, offset=0):
        raise ValueError

    def slice(self, res, start, stop):
        for i in range(start, stop):
            res[i - start] = self[i]
        return res

    def slice_view(self, start, stop):
        return KeyVSliced(self, start, stop)


_CHBITS = const(5)
_CHSIZE = const(1 << _CHBITS)


class KeyV(KeyVBase):
    """
    KeyVector abstraction
    Constant precomputed buffers = bytes, frozen. Same operation as normal.

    Non-constant KeyVector is separated to _CHSIZE elements chunks to avoid problems with
    the heap fragmentation. In this it is more probable that the chunks are correctly
    allocated as smaller continuous memory is required. Chunk is assumed to
    have _CHSIZE elements at all times to minimize corner cases handling. BP require either
    multiple of _CHSIZE elements vectors or less than _CHSIZE.

    Some chunk-dependent cases are not implemented as they are currently not needed in the BP.
    """

    __slots__ = ("current_idx", "size", "d", "mv", "const", "cur", "chunked")

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
        if elems > _CHSIZE and elems % _CHSIZE == 0:
            self.chunked = True
            gc.collect()
            self.d = [bytearray(32 * _CHSIZE) for _ in range(elems // _CHSIZE)]

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
            return self.to(item)
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
                self.d[idx >> _CHBITS],
                (idx & (_CHSIZE - 1)) << 5,
                32,
            )
        else:
            memcpy(buff if buff else self.cur, offset, self.d, idx << 5, 32)
        return buff if buff else self.cur

    def read(self, idx, buff, offset=0):
        idx = self.idxize(idx)
        if self.chunked:
            memcpy(self.d[idx >> _CHBITS], (idx & (_CHSIZE - 1)) << 5, buff, offset, 32)
        else:
            memcpy(self.d, idx << 5, buff, offset, 32)

    def resize(self, nsize, chop=False, realloc=False):
        if self.size == nsize:
            return

        if self.chunked and nsize <= _CHSIZE:
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

        elif self.chunked and self.size < nsize:
            if nsize % _CHSIZE != 0 or realloc or chop:
                raise ValueError("Unsupported")  # not needed
            for i in range((nsize - self.size) // _CHSIZE):
                self.d.append(bytearray(32 * _CHSIZE))

        elif self.chunked:
            if nsize % _CHSIZE != 0:
                raise ValueError("Unsupported")  # not needed
            for i in range((self.size - nsize) // _CHSIZE):
                self.d.pop()
            if realloc:
                for i in range(nsize // _CHSIZE):
                    self.d[i] = bytearray(self.d[i])

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

        elif self.chunked and not src.chunked or self.chunked and src.chunked:
            for i in range(nsize):
                self.read(i, src.to(i + offset))

        elif not self.chunked and src.chunked:
            for i in range(nsize >> _CHBITS):
                memcpy(
                    self.d,
                    i << 11,
                    src.d[i + (offset >> _CHBITS)],
                    (offset & (_CHSIZE - 1)) << 5 if i == 0 else 0,
                    nsize << 5 if i <= nsize >> _CHBITS else (nsize & _CHSIZE) << 5,
                )


class KeyVEval(KeyVBase):
    """
    KeyVector computed / evaluated on demand
    """

    __slots__ = ("current_idx", "size", "fnc", "raw", "scalar", "buff")

    def __init__(self, elems=64, src=None, raw=False, scalar=True):
        super().__init__(elems)
        self.fnc = src
        self.raw = raw
        self.scalar = scalar
        self.buff = (
            _ensure_dst_key()
            if not raw
            else (crypto.new_scalar() if scalar else crypto.new_point())
        )

    def __getitem__(self, item):
        return self.fnc(self.idxize(item), self.buff)

    def to(self, idx, buff=None, offset=0):
        self.fnc(self.idxize(idx), self.buff)
        if self.raw:
            if offset != 0:
                raise ValueError("Not supported")
            if self.scalar and buff:
                return crypto.sc_copy(buff, self.buff)
            elif self.scalar:
                return self.buff
            else:
                raise ValueError("Not supported")
        else:
            memcpy(buff, offset, self.buff, 0, 32)
        return buff if buff else self.buff


class KeyVSized(KeyVBase):
    """
    Resized vector, wrapping possibly larger vector
    (e.g., precomputed, but has to have exact size for further computations)
    """

    __slots__ = ("current_idx", "size", "wrapped")

    def __init__(self, wrapped, new_size):
        super().__init__(new_size)
        self.wrapped = wrapped

    def __getitem__(self, item):
        return self.wrapped[self.idxize(item)]

    def __setitem__(self, key, value):
        self.wrapped[self.idxize(key)] = value


class KeyVConst(KeyVBase):
    __slots__ = ("current_idx", "size", "elem")

    def __init__(self, size, elem, copy=True):
        super().__init__(size)
        self.elem = _init_key(elem) if copy else elem

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

    __slots__ = ("current_idx", "size", "precomp_prefix", "aux_comp_fnc", "buff")

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

    __slots__ = ("current_idx", "size", "wrapped", "offset")

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

    __slots__ = ("current_idx", "size", "x", "raw", "cur", "last_idx")

    def __init__(self, size, x, raw=False, **kwargs):
        super().__init__(size)
        self.x = x if not raw else crypto.decodeint_into_noreduce(None, x)
        self.raw = raw
        self.cur = bytearray(32) if not raw else crypto.new_scalar()
        self.last_idx = 0

    def __getitem__(self, item):
        prev = self.last_idx
        item = self.idxize(item)
        self.last_idx = item

        if item == 0:
            return (
                _copy_key(self.cur, _ONE)
                if not self.raw
                else crypto.decodeint_into_noreduce(None, _ONE)
            )
        elif item == 1:
            return (
                _copy_key(self.cur, self.x)
                if not self.raw
                else crypto.sc_copy(self.cur, self.x)
            )
        elif item == prev:
            return self.cur
        elif item == prev + 1:
            return (
                _sc_mul(self.cur, self.cur, self.x)
                if not self.raw
                else crypto.sc_mul_into(self.cur, self.cur, self.x)
            )
        else:
            raise IndexError(f"Only linear scan allowed: {prev}, {item}")

    def set_state(self, idx, val):
        self.last_idx = idx
        if self.raw:
            return crypto.sc_copy(self.cur, val)
        else:
            return _copy_key(self.cur, val)


class KeyR0(KeyVBase):
    """
    Vector r0. Allows only sequential access (no jumping). Resets on [0,1] access.
    zt_i = z^{2 + \floor{i/N}} 2^{i % N}
    r0_i = ((a_{Ri} + z) y^{i}) + zt_i

    Could be composed from smaller vectors, but RAW returns are required
    """

    __slots__ = (
        "current_idx",
        "size",
        "N",
        "aR",
        "raw",
        "y",
        "yp",
        "z",
        "zt",
        "p2",
        "res",
        "cur",
        "last_idx",
    )

    def __init__(self, size, N, aR, y, z, raw=False, **kwargs):
        super().__init__(size)
        self.N = N
        self.aR = aR
        self.raw = raw
        self.y = crypto.decodeint_into_noreduce(None, y)
        self.yp = crypto.new_scalar()  # y^{i}
        self.z = crypto.decodeint_into_noreduce(None, z)
        self.zt = crypto.new_scalar()  # z^{2 + \floor{i/N}}
        self.p2 = crypto.new_scalar()  # 2^{i \% N}
        self.res = crypto.new_scalar()  # tmp_sc_1

        self.cur = bytearray(32) if not raw else None
        self.last_idx = 0
        self.reset()

    def reset(self):
        crypto.decodeint_into_noreduce(self.yp, _ONE)
        crypto.decodeint_into_noreduce(self.p2, _ONE)
        crypto.sc_mul_into(self.zt, self.z, self.z)

    def __getitem__(self, item):
        prev = self.last_idx
        item = self.idxize(item)
        self.last_idx = item

        # Const init for eval
        if item == 0:  # Reset on first item access
            self.reset()

        elif item == prev + 1:
            crypto.sc_mul_into(self.yp, self.yp, self.y)  # ypow
            if item % self.N == 0:
                crypto.sc_mul_into(self.zt, self.zt, self.z)  # zt
                crypto.decodeint_into_noreduce(self.p2, _ONE)  # p2 reset
            else:
                crypto.decodeint_into_noreduce(self.res, _TWO)  # p2
                crypto.sc_mul_into(self.p2, self.p2, self.res)  # p2

        elif item == prev:  # No advancing
            pass

        else:
            raise IndexError("Only linear scan allowed")

        # Eval r0[i]
        if (
            item == 0 or item != prev
        ):  # if True not present, fails with cross dot product
            crypto.decodeint_into_noreduce(self.res, self.aR.to(item))  # aR[i]
            crypto.sc_add_into(self.res, self.res, self.z)  # aR[i] + z
            crypto.sc_mul_into(self.res, self.res, self.yp)  # (aR[i] + z) * y^i
            crypto.sc_muladd_into(
                self.res, self.zt, self.p2, self.res
            )  # (aR[i] + z) * y^i + z^{2 + \floor{i/N}} 2^{i \% N}

        if self.raw:
            return self.res

        crypto.encodeint_into(self.cur, self.res)
        return self.cur

    def to(self, idx, buff=None, offset=0):
        r = self[idx]
        if buff is None:
            return r
        return memcpy(buff, offset, r, 0, 32)


def _ensure_dst_keyvect(dst=None, size=None):
    if dst is None:
        dst = KeyV(elems=size)
        return dst
    if size is not None and size != len(dst):
        dst.resize(size)
    return dst


def _const_vector(val, elems=_BP_N, copy=True):
    return KeyVConst(elems, val, copy)


def _vector_exponent_custom(A, B, a, b, dst=None, a_raw=None, b_raw=None):
    """
    \\sum_{i=0}^{|A|}  a_i A_i + b_i B_i
    """
    dst = _ensure_dst_key(dst)
    crypto.identity_into(_tmp_pt_2)

    for i in range(len(a or a_raw)):
        if a:
            crypto.decodeint_into_noreduce(_tmp_sc_1, a.to(i))
        crypto.decodepoint_into(_tmp_pt_3, A.to(i))
        if b:
            crypto.decodeint_into_noreduce(_tmp_sc_2, b.to(i))
        crypto.decodepoint_into(_tmp_pt_4, B.to(i))
        crypto.add_keys3_into(
            _tmp_pt_1,
            _tmp_sc_1 if a else a_raw.to(i),
            _tmp_pt_3,
            _tmp_sc_2 if b else b_raw.to(i),
            _tmp_pt_4,
        )
        crypto.point_add_into(_tmp_pt_2, _tmp_pt_2, _tmp_pt_1)
        _gc_iter(i)
    crypto.encodepoint_into(dst, _tmp_pt_2)
    return dst


def _vector_powers(x, n, dst=None, dynamic=False, **kwargs):
    """
    r_i = x^i
    """
    if dynamic:
        return KeyVPowers(n, x, **kwargs)
    dst = _ensure_dst_keyvect(dst, n)
    if n == 0:
        return dst
    dst.read(0, _ONE)
    if n == 1:
        return dst
    dst.read(1, x)

    crypto.decodeint_into_noreduce(_tmp_sc_1, x)
    crypto.decodeint_into_noreduce(_tmp_sc_2, x)
    for i in range(2, n):
        crypto.sc_mul_into(_tmp_sc_1, _tmp_sc_1, _tmp_sc_2)
        crypto.encodeint_into(_tmp_bf_0, _tmp_sc_1)
        dst.read(i, _tmp_bf_0)
        _gc_iter(i)
    return dst


def _vector_power_sum(x, n, dst=None):
    """
    \\sum_{i=0}^{n-1} x^i
    """
    dst = _ensure_dst_key(dst)
    if n == 0:
        return _copy_key(dst, _ZERO)
    if n == 1:
        _copy_key(dst, _ONE)

    crypto.decodeint_into_noreduce(_tmp_sc_1, x)
    crypto.decodeint_into_noreduce(_tmp_sc_3, _ONE)
    crypto.sc_add_into(_tmp_sc_3, _tmp_sc_3, _tmp_sc_1)
    crypto.sc_copy(_tmp_sc_2, _tmp_sc_1)

    for i in range(2, n):
        crypto.sc_mul_into(_tmp_sc_2, _tmp_sc_2, _tmp_sc_1)
        crypto.sc_add_into(_tmp_sc_3, _tmp_sc_3, _tmp_sc_2)
        _gc_iter(i)

    return crypto.encodeint_into(dst, _tmp_sc_3)


def _inner_product(a, b, dst=None):
    """
    \\sum_{i=0}^{|a|} a_i b_i
    """
    if len(a) != len(b):
        raise ValueError("Incompatible sizes of a and b")
    dst = _ensure_dst_key(dst)
    crypto.sc_init_into(_tmp_sc_1, 0)

    for i in range(len(a)):
        crypto.decodeint_into_noreduce(_tmp_sc_2, a.to(i))
        crypto.decodeint_into_noreduce(_tmp_sc_3, b.to(i))
        crypto.sc_muladd_into(_tmp_sc_1, _tmp_sc_2, _tmp_sc_3, _tmp_sc_1)
        _gc_iter(i)

    crypto.encodeint_into(dst, _tmp_sc_1)
    return dst


def _hadamard_fold(v, a, b, into=None, into_offset=0, vR=None, vRoff=0):
    """
    Folds a curvepoint array using a two way scaled Hadamard product

    ln = len(v); h = ln // 2
    v_i = a v_i + b v_{h + i}
    """
    h = len(v) // 2
    crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    crypto.decodeint_into_noreduce(_tmp_sc_2, b)
    into = into if into else v

    for i in range(h):
        crypto.decodepoint_into(_tmp_pt_1, v.to(i))
        crypto.decodepoint_into(_tmp_pt_2, v.to(h + i) if not vR else vR.to(i + vRoff))
        crypto.add_keys3_into(_tmp_pt_3, _tmp_sc_1, _tmp_pt_1, _tmp_sc_2, _tmp_pt_2)
        crypto.encodepoint_into(_tmp_bf_0, _tmp_pt_3)
        into.read(i + into_offset, _tmp_bf_0)
        _gc_iter(i)

    return into


def _hadamard_fold_linear(v, a, b, into=None, into_offset=0):
    """
    Folds a curvepoint array using a two way scaled Hadamard product.
    Iterates v linearly to support linear-scan evaluated vectors (on the fly)

    ln = len(v); h = ln // 2
    v_i = a v_i + b v_{h + i}
    """
    h = len(v) // 2
    into = into if into else v

    crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    for i in range(h):
        crypto.decodepoint_into(_tmp_pt_1, v.to(i))
        crypto.scalarmult_into(_tmp_pt_1, _tmp_pt_1, _tmp_sc_1)
        crypto.encodepoint_into(_tmp_bf_0, _tmp_pt_1)
        into.read(i + into_offset, _tmp_bf_0)
        _gc_iter(i)

    crypto.decodeint_into_noreduce(_tmp_sc_1, b)
    for i in range(h):
        crypto.decodepoint_into(_tmp_pt_1, v.to(i + h))
        crypto.scalarmult_into(_tmp_pt_1, _tmp_pt_1, _tmp_sc_1)
        crypto.decodepoint_into(_tmp_pt_2, into.to(i + into_offset))
        crypto.point_add_into(_tmp_pt_1, _tmp_pt_1, _tmp_pt_2)
        crypto.encodepoint_into(_tmp_bf_0, _tmp_pt_1)
        into.read(i + into_offset, _tmp_bf_0)

        _gc_iter(i)
    return into


def _scalar_fold(v, a, b, into=None, into_offset=0):
    """
    ln = len(v); h = ln // 2
    v_i = a v_i + b v_{h + i}
    """
    h = len(v) // 2
    crypto.decodeint_into_noreduce(_tmp_sc_1, a)
    crypto.decodeint_into_noreduce(_tmp_sc_2, b)
    into = into if into else v

    for i in range(h):
        crypto.decodeint_into_noreduce(_tmp_sc_3, v.to(i))
        crypto.decodeint_into_noreduce(_tmp_sc_4, v.to(h + i))
        crypto.sc_mul_into(_tmp_sc_3, _tmp_sc_3, _tmp_sc_1)
        crypto.sc_mul_into(_tmp_sc_4, _tmp_sc_4, _tmp_sc_2)
        crypto.sc_add_into(_tmp_sc_3, _tmp_sc_3, _tmp_sc_4)
        crypto.encodeint_into(_tmp_bf_0, _tmp_sc_3)
        into.read(i + into_offset, _tmp_bf_0)
        _gc_iter(i)

    return into


def _cross_inner_product(l0, r0, l1, r1):
    """
    t1   = l0 . r1 + l1 . r0
    t2   = l1 . r1
    """
    sc_t1 = crypto.new_scalar()
    sc_t2 = crypto.new_scalar()
    tl = crypto.new_scalar()
    tr = crypto.new_scalar()

    for i in range(len(l0)):
        crypto.decodeint_into_noreduce(tl, l0.to(i))
        crypto.decodeint_into_noreduce(tr, r1.to(i))
        crypto.sc_muladd_into(sc_t1, tl, tr, sc_t1)

        crypto.decodeint_into_noreduce(tl, l1.to(i))
        crypto.sc_muladd_into(sc_t2, tl, tr, sc_t2)

        crypto.decodeint_into_noreduce(tr, r0.to(i))
        crypto.sc_muladd_into(sc_t1, tl, tr, sc_t1)

        _gc_iter(i)

    return crypto.encodeint(sc_t1), crypto.encodeint(sc_t2)


def _vector_gen(dst, size, op):
    dst = _ensure_dst_keyvect(dst, size)
    for i in range(size):
        dst.to(i, _tmp_bf_0)
        op(i, _tmp_bf_0)
        dst.read(i, _tmp_bf_0)
        _gc_iter(i)
    return dst


def _vector_dup(x, n, dst=None):
    dst = _ensure_dst_keyvect(dst, n)
    for i in range(n):
        dst[i] = x
        _gc_iter(i)
    return dst


def _hash_cache_mash(dst, hash_cache, *args):
    dst = _ensure_dst_key(dst)
    ctx = crypto.get_keccak()
    ctx.update(hash_cache)

    for x in args:
        if x is None:
            break
        ctx.update(x)
    hsh = ctx.digest()

    crypto.decodeint_into(_tmp_sc_1, hsh)
    crypto.encodeint_into(hash_cache, _tmp_sc_1)
    _copy_key(dst, hash_cache)
    return dst


def _is_reduced(sc):
    return crypto.encodeint_into(_tmp_bf_0, crypto.decodeint_into(_tmp_sc_1, sc)) == sc


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
        crypto.decodeint_into_noreduce(_tmp_sc_1, scalar)
        crypto.decodepoint_into(_tmp_pt_2, point)
        crypto.scalarmult_into(_tmp_pt_3, _tmp_pt_2, _tmp_sc_1)
        crypto.point_add_into(self.acc, self.acc, _tmp_pt_3)
        self.current_idx += 1
        self.size += 1

    def eval(self, dst, GiHi=False):
        dst = _ensure_dst_key(dst)
        return crypto.encodepoint_into(dst, self.acc)


def _multiexp(dst=None, data=None, GiHi=False):
    return data.eval(dst, GiHi)


class BulletProofBuilder:
    def __init__(self):
        self.use_det_masks = True
        self.proof_sec = None

        # BP_GI_PRE = get_exponent(Gi[i], _XMR_H, i * 2 + 1)
        self.Gprec = KeyV(buffer=crypto.tcry.BP_GI_PRE, const=True)
        # BP_HI_PRE = get_exponent(Hi[i], _XMR_H, i * 2)
        self.Hprec = KeyV(buffer=crypto.tcry.BP_HI_PRE, const=True)
        # BP_TWO_N = vector_powers(_TWO, _BP_N);
        self.twoN = KeyV(buffer=crypto.tcry.BP_TWO_N, const=True)
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
            j, i = idx // _BP_N, idx % _BP_N
            r = None
            if j >= num_inp:
                r = _ZERO if is_a else _MINUS_ONE
            elif sv[j][i // 8] & (1 << i % 8):
                r = _ONE if is_a else _ZERO
            else:
                r = _ZERO if is_a else _MINUS_ONE
            if d:
                return memcpy(d, 0, r, 0, 32)
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
        memcpy(self.tmp_det_buff, 65, _ZERO, 0, 4)
        dump_uvarint_b_into(i, self.tmp_det_buff, 65)
        crypto.hash_to_scalar_into(self.tmp_sc_1, self.tmp_det_buff)
        crypto.encodeint_into(dst, self.tmp_sc_1)
        return dst

    def _gprec_aux(self, size):
        return KeyVPrecomp(
            size, self.Gprec, lambda i, d: _get_exponent(d, _XMR_H, i * 2 + 1)
        )

    def _hprec_aux(self, size):
        return KeyVPrecomp(
            size, self.Hprec, lambda i, d: _get_exponent(d, _XMR_H, i * 2)
        )

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
            return _sc_mul(d, lw, rw)

        return KeyVPrecomp(size, self.twoN, pow_two)

    def sL_vct(self, ln=_BP_N):
        return (
            KeyVEval(ln, lambda i, dst: self._det_mask(i, True, dst))
            if self.use_det_masks
            else self.sX_gen(ln)
        )

    def sR_vct(self, ln=_BP_N):
        return (
            KeyVEval(ln, lambda i, dst: self._det_mask(i, False, dst))
            if self.use_det_masks
            else self.sX_gen(ln)
        )

    def sX_gen(self, ln=_BP_N):
        gc.collect()
        buff = bytearray(ln * 32)
        buff_mv = memoryview(buff)
        sc = crypto.new_scalar()
        for i in range(ln):
            crypto.random_scalar(sc)
            crypto.encodeint_into(buff_mv[i * 32 : (i + 1) * 32], sc)
            _gc_iter(i)
        return KeyV(buffer=buff)

    def vector_exponent(self, a, b, dst=None, a_raw=None, b_raw=None):
        return _vector_exponent_custom(self.Gprec, self.Hprec, a, b, dst, a_raw, b_raw)

    def prove(self, sv, gamma):
        return self.prove_batch([sv], [gamma])

    def prove_setup(self, sv, gamma):
        utils.ensure(len(sv) == len(gamma), "|sv| != |gamma|")
        utils.ensure(len(sv) > 0, "sv empty")

        self.proof_sec = crypto.random_bytes(64)
        self._det_mask_init()
        gc.collect()
        sv = [crypto.encodeint(x) for x in sv]
        gamma = [crypto.encodeint(x) for x in gamma]

        M, logM = 1, 0
        while M <= _BP_M and M < len(sv):
            logM += 1
            M = 1 << logM
        MN = M * _BP_N

        V = _ensure_dst_keyvect(None, len(sv))
        for i in range(len(sv)):
            _add_keys2(_tmp_bf_0, gamma[i], sv[i], _XMR_H)
            _scalarmult_key(_tmp_bf_0, _tmp_bf_0, _INV_EIGHT)
            V.read(i, _tmp_bf_0)

        aL, aR = self.aX_vcts(sv, MN)
        return M, logM, aL, aR, V, gamma

    def prove_batch(self, sv, gamma):
        M, logM, aL, aR, V, gamma = self.prove_setup(sv, gamma)
        hash_cache = _ensure_dst_key()
        while True:
            self.gc(10)
            r = self._prove_batch_main(
                V, gamma, aL, aR, hash_cache, logM, _BP_LOG_N, M, _BP_N
            )
            if r[0]:
                break
        return r[1]

    def _prove_batch_main(self, V, gamma, aL, aR, hash_cache, logM, logN, M, N):
        logMN = logM + logN
        MN = M * N
        _hash_vct_to_scalar(hash_cache, V)

        # Extended precomputed GiHi
        Gprec = self._gprec_aux(MN)
        Hprec = self._hprec_aux(MN)

        # PHASE 1
        A, S, T1, T2, taux, mu, t, l, r, y, x_ip, hash_cache = self._prove_phase1(
            N, M, logMN, V, gamma, aL, aR, hash_cache, Gprec, Hprec
        )

        # PHASE 2
        L, R, a, b = self._prove_loop(
            MN, logMN, l, r, y, x_ip, hash_cache, Gprec, Hprec
        )

        from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import Bulletproof

        return (
            1,
            Bulletproof(
                V=V, A=A, S=S, T1=T1, T2=T2, taux=taux, mu=mu, L=L, R=R, a=a, b=b, t=t
            ),
        )

    def _prove_phase1(self, N, M, logMN, V, gamma, aL, aR, hash_cache, Gprec, Hprec):
        MN = M * N

        # PAPER LINES 38-39, compute A = 8^{-1} ( \alpha G + \sum_{i=0}^{MN-1} a_{L,i} \Gi_i + a_{R,i} \Hi_i)
        alpha = _sc_gen()
        A = _ensure_dst_key()
        _vector_exponent_custom(Gprec, Hprec, aL, aR, A)
        _add_keys(A, A, _scalarmult_base(_tmp_bf_1, alpha))
        _scalarmult_key(A, A, _INV_EIGHT)
        self.gc(11)

        # PAPER LINES 40-42, compute S =  8^{-1} ( \rho G + \sum_{i=0}^{MN-1} s_{L,i} \Gi_i + s_{R,i} \Hi_i)
        sL = self.sL_vct(MN)
        sR = self.sR_vct(MN)
        rho = _sc_gen()
        S = _ensure_dst_key()
        _vector_exponent_custom(Gprec, Hprec, sL, sR, S)
        _add_keys(S, S, _scalarmult_base(_tmp_bf_1, rho))
        _scalarmult_key(S, S, _INV_EIGHT)
        self.gc(12)

        # PAPER LINES 43-45
        y = _ensure_dst_key()
        _hash_cache_mash(y, hash_cache, A, S)
        if y == _ZERO:
            return (0,)

        z = _ensure_dst_key()
        _hash_to_scalar(hash_cache, y)
        _copy_key(z, hash_cache)
        zc = crypto.decodeint_into_noreduce(None, z)
        if z == _ZERO:
            return (0,)

        # Polynomial construction by coefficients
        # l0 = aL - z           r0   = ((aR + z) . ypow) + zt
        # l1 = sL               r1   =   sR      . ypow
        l0 = KeyVEval(
            MN, lambda i, d: _sc_sub(d, aL.to(i), None, None, zc)  # noqa: F821
        )
        l1 = sL
        self.gc(13)

        # This computes the ugly sum/concatenation from PAPER LINE 65
        # r0_i = ((a_{Ri} + z) y^{i}) + zt_i
        # r1_i = s_{Ri} y^{i}
        r0 = KeyR0(MN, N, aR, y, z)
        ypow = KeyVPowers(MN, y, raw=True)
        r1 = KeyVEval(
            MN, lambda i, d: _sc_mul(d, sR.to(i), None, ypow[i])  # noqa: F821
        )
        del aR
        self.gc(14)

        # Evaluate per index
        #  - $t_1 = l_0 . r_1 + l_1 . r0$
        #  - $t_2 = l_1 . r_1$
        #  - compute then T1, T2, x
        t1, t2 = _cross_inner_product(l0, r0, l1, r1)

        # PAPER LINES 47-48, Compute: T1, T2
        # T1 = 8^{-1} (\tau_1G + t_1H )
        # T2 = 8^{-1} (\tau_2G + t_2H )
        tau1, tau2 = _sc_gen(), _sc_gen()
        T1, T2 = _ensure_dst_key(), _ensure_dst_key()

        _add_keys2(T1, tau1, t1, _XMR_H)
        _scalarmult_key(T1, T1, _INV_EIGHT)

        _add_keys2(T2, tau2, t2, _XMR_H)
        _scalarmult_key(T2, T2, _INV_EIGHT)
        del (t1, t2)
        self.gc(16)

        # PAPER LINES 49-51, compute x
        x = _ensure_dst_key()
        _hash_cache_mash(x, hash_cache, z, T1, T2)
        if x == _ZERO:
            return (0,)

        # Second pass, compute l, r
        # Offloaded version does this incrementally and produces l, r outs in chunks
        # Message offloaded sends blinded vectors with random constants.
        #  - $l_i = l_{0,i} + xl_{1,i}
        #  - $r_i = r_{0,i} + xr_{1,i}
        #  - $t   = l . r$
        l = _ensure_dst_keyvect(None, MN)
        r = _ensure_dst_keyvect(None, MN)
        ts = crypto.new_scalar()
        for i in range(MN):
            _sc_muladd(_tmp_bf_0, x, l1.to(i), l0.to(i))
            l.read(i, _tmp_bf_0)

            _sc_muladd(_tmp_bf_1, x, r1.to(i), r0.to(i))
            r.read(i, _tmp_bf_1)

            _sc_muladd(ts, _tmp_bf_0, _tmp_bf_1, None, c_raw=ts, raw=True)

        t = crypto.encodeint(ts)
        del (l0, l1, sL, sR, r0, r1, ypow, ts)
        self.gc(17)

        # PAPER LINES 52-53, Compute \tau_x
        taux = _ensure_dst_key()
        _sc_mul(taux, tau1, x)
        _sc_mul(_tmp_bf_0, x, x)
        _sc_muladd(taux, tau2, _tmp_bf_0, taux)
        del (tau1, tau2)

        zpow = crypto.sc_mul_into(None, zc, zc)
        for j in range(1, len(V) + 1):
            _sc_muladd(taux, None, gamma[j - 1], taux, a_raw=zpow)
            crypto.sc_mul_into(zpow, zpow, zc)
        del (zc, zpow)

        self.gc(18)
        mu = _ensure_dst_key()
        _sc_muladd(mu, x, rho, alpha)
        del (rho, alpha)
        self.gc(19)

        # PAPER LINES 32-33
        x_ip = _hash_cache_mash(None, hash_cache, x, taux, mu, t)
        if x_ip == _ZERO:
            return 0, None

        return A, S, T1, T2, taux, mu, t, l, r, y, x_ip, hash_cache

    def _prove_loop(self, MN, logMN, l, r, y, x_ip, hash_cache, Gprec, Hprec):
        nprime = MN
        aprime = l
        bprime = r

        yinvpowL = KeyVPowers(MN, _invert(_tmp_bf_0, y), raw=True)
        yinvpowR = KeyVPowers(MN, _tmp_bf_0, raw=True)
        tmp_pt = crypto.new_point()

        Gprime = Gprec
        HprimeL = KeyVEval(
            MN, lambda i, d: _scalarmult_key(d, Hprec.to(i), None, yinvpowL[i])
        )
        HprimeR = KeyVEval(
            MN, lambda i, d: _scalarmult_key(d, Hprec.to(i), None, yinvpowR[i], tmp_pt)
        )
        Hprime = HprimeL
        self.gc(20)

        L = _ensure_dst_keyvect(None, logMN)
        R = _ensure_dst_keyvect(None, logMN)
        cL = _ensure_dst_key()
        cR = _ensure_dst_key()
        winv = _ensure_dst_key()
        w_round = _ensure_dst_key()
        tmp = _ensure_dst_key()
        _tmp_k_1 = _ensure_dst_key()
        round = 0

        # PAPER LINE 13
        while nprime > 1:
            # PAPER LINE 15
            npr2 = nprime
            nprime >>= 1
            self.gc(22)

            # PAPER LINES 16-17
            # cL = \ap_{\left(\inta\right)} \cdot \bp_{\left(\intb\right)}
            # cR = \ap_{\left(\intb\right)} \cdot \bp_{\left(\inta\right)}
            _inner_product(
                aprime.slice_view(0, nprime), bprime.slice_view(nprime, npr2), cL
            )

            _inner_product(
                aprime.slice_view(nprime, npr2), bprime.slice_view(0, nprime), cR
            )
            self.gc(23)

            # PAPER LINES 18-19
            # Lc = 8^{-1} \left(\left( \sum_{i=0}^{\np} \ap_{i}\quad\Gp_{i+\np} + \bp_{i+\np}\Hp_{i} \right)
            # 		    + \left(c_L x_{ip}\right)H \right)
            _vector_exponent_custom(
                Gprime.slice_view(nprime, npr2),
                Hprime.slice_view(0, nprime),
                aprime.slice_view(0, nprime),
                bprime.slice_view(nprime, npr2),
                _tmp_bf_0,
            )

            # In round 0 backup the y^{prime - 1}
            if round == 0:
                yinvpowR.set_state(yinvpowL.last_idx, yinvpowL.cur)

            _sc_mul(tmp, cL, x_ip)
            _add_keys(_tmp_bf_0, _tmp_bf_0, _scalarmultH(_tmp_k_1, tmp))
            _scalarmult_key(_tmp_bf_0, _tmp_bf_0, _INV_EIGHT)
            L.read(round, _tmp_bf_0)
            self.gc(24)

            # Rc = 8^{-1} \left(\left( \sum_{i=0}^{\np} \ap_{i+\np}\Gp_{i}\quad + \bp_{i}\quad\Hp_{i+\np} \right)
            #           + \left(c_R x_{ip}\right)H \right)
            _vector_exponent_custom(
                Gprime.slice_view(0, nprime),
                Hprime.slice_view(nprime, npr2),
                aprime.slice_view(nprime, npr2),
                bprime.slice_view(0, nprime),
                _tmp_bf_0,
            )

            _sc_mul(tmp, cR, x_ip)
            _add_keys(_tmp_bf_0, _tmp_bf_0, _scalarmultH(_tmp_k_1, tmp))
            _scalarmult_key(_tmp_bf_0, _tmp_bf_0, _INV_EIGHT)
            R.read(round, _tmp_bf_0)
            self.gc(25)

            # PAPER LINES 21-22
            _hash_cache_mash(w_round, hash_cache, L.to(round), R.to(round))
            if w_round == _ZERO:
                return (0,)

            # PAPER LINES 24-25, fold {G~, H~}
            _invert(winv, w_round)
            self.gc(26)

            # PAPER LINES 28-29, fold {a, b} vectors
            # aprime's high part is used as a buffer for other operations
            _scalar_fold(aprime, w_round, winv)
            aprime.resize(nprime)
            self.gc(27)

            _scalar_fold(bprime, winv, w_round)
            bprime.resize(nprime)
            self.gc(28)

            # First fold produced to a new buffer, smaller one (G~ on-the-fly)
            Gprime_new = KeyV(nprime) if round == 0 else Gprime
            Gprime = _hadamard_fold(Gprime, winv, w_round, Gprime_new, 0)
            Gprime.resize(nprime)
            self.gc(30)

            # Hadamard fold for H is special - linear scan only.
            # Linear scan is slow, thus we have HprimeR.
            if round == 0:
                Hprime_new = KeyV(nprime)
                Hprime = _hadamard_fold(
                    Hprime, w_round, winv, Hprime_new, 0, HprimeR, nprime
                )
                # Hprime = _hadamard_fold_linear(Hprime, w_round, winv, Hprime_new, 0)

            else:
                _hadamard_fold(Hprime, w_round, winv)
                Hprime.resize(nprime)

            if round == 0:
                # del (Gprec, Hprec, yinvpowL, HprimeL)
                del (Gprec, Hprec, yinvpowL, yinvpowR, HprimeL, HprimeR, tmp_pt)

            self.gc(31)
            round += 1

        return L, R, aprime.to(0), bprime.to(0)

    def verify(self, proof):
        return self.verify_batch([proof])

    def verify_batch(self, proofs, single_optim=True):
        """
        BP batch verification
        :param proofs:
        :param single_optim: single proof memory optimization
        :return:
        """
        max_length = 0
        for proof in proofs:
            utils.ensure(_is_reduced(proof.taux), "Input scalar not in range")
            utils.ensure(_is_reduced(proof.mu), "Input scalar not in range")
            utils.ensure(_is_reduced(proof.a), "Input scalar not in range")
            utils.ensure(_is_reduced(proof.b), "Input scalar not in range")
            utils.ensure(_is_reduced(proof.t), "Input scalar not in range")
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
        z1 = _init_key(_ZERO)
        z3 = _init_key(_ZERO)
        m_z4 = _vector_dup(_ZERO, maxMN) if not is_single else None
        m_z5 = _vector_dup(_ZERO, maxMN) if not is_single else None
        m_y0 = _init_key(_ZERO)
        y1 = _init_key(_ZERO)
        muex_acc = _init_key(_ONE)

        Gprec = self._gprec_aux(maxMN)
        Hprec = self._hprec_aux(maxMN)

        for proof in proofs:
            M = 1
            logM = 0
            while M <= _BP_M and M < len(proof.V):
                logM += 1
                M = 1 << logM

            utils.ensure(len(proof.L) == 6 + logM, "Proof is not the expected size")
            MN = M * N
            weight_y = crypto.encodeint(crypto.random_scalar())
            weight_z = crypto.encodeint(crypto.random_scalar())

            # Reconstruct the challenges
            hash_cache = _hash_vct_to_scalar(None, proof.V)
            y = _hash_cache_mash(None, hash_cache, proof.A, proof.S)
            utils.ensure(y != _ZERO, "y == 0")
            z = _hash_to_scalar(None, y)
            _copy_key(hash_cache, z)
            utils.ensure(z != _ZERO, "z == 0")

            x = _hash_cache_mash(None, hash_cache, z, proof.T1, proof.T2)
            utils.ensure(x != _ZERO, "x == 0")
            x_ip = _hash_cache_mash(None, hash_cache, x, proof.taux, proof.mu, proof.t)
            utils.ensure(x_ip != _ZERO, "x_ip == 0")

            # PAPER LINE 61
            _sc_mulsub(m_y0, proof.taux, weight_y, m_y0)
            zpow = _vector_powers(z, M + 3)

            k = _ensure_dst_key()
            ip1y = _vector_power_sum(y, MN)
            _sc_mulsub(k, zpow.to(2), ip1y, _ZERO)
            for j in range(1, M + 1):
                utils.ensure(j + 2 < len(zpow), "invalid zpow index")
                _sc_mulsub(k, zpow.to(j + 2), _BP_IP12, k)

            # VERIFY_line_61rl_new
            _sc_muladd(tmp, z, ip1y, k)
            _sc_sub(tmp, proof.t, tmp)

            _sc_muladd(y1, tmp, weight_y, y1)
            weight_y8 = _init_key(weight_y)
            weight_y8 = _sc_mul(None, weight_y, _EIGHT)

            muex = MultiExpSequential(points=[pt for pt in proof.V])
            for j in range(len(proof.V)):
                _sc_mul(tmp, zpow.to(j + 2), weight_y8)
                muex.add_scalar(_init_key(tmp))

            _sc_mul(tmp, x, weight_y8)
            muex.add_pair(_init_key(tmp), proof.T1)

            xsq = _ensure_dst_key()
            _sc_mul(xsq, x, x)

            _sc_mul(tmp, xsq, weight_y8)
            muex.add_pair(_init_key(tmp), proof.T2)

            weight_z8 = _init_key(weight_z)
            weight_z8 = _sc_mul(None, weight_z, _EIGHT)

            muex.add_pair(weight_z8, proof.A)
            _sc_mul(tmp, x, weight_z8)
            muex.add_pair(_init_key(tmp), proof.S)

            _multiexp(tmp, muex, False)
            _add_keys(muex_acc, muex_acc, tmp)
            del muex

            # Compute the number of rounds for the inner product
            rounds = logM + logN
            utils.ensure(rounds > 0, "Zero rounds")

            # PAPER LINES 21-22
            # The inner product challenges are computed per round
            w = _ensure_dst_keyvect(None, rounds)
            for i in range(rounds):
                _hash_cache_mash(_tmp_bf_0, hash_cache, proof.L[i], proof.R[i])
                w.read(i, _tmp_bf_0)
                utils.ensure(w.to(i) != _ZERO, "w[i] == 0")

            # Basically PAPER LINES 24-25
            # Compute the curvepoints from G[i] and H[i]
            yinvpow = _init_key(_ONE)
            ypow = _init_key(_ONE)
            yinv = _invert(None, y)
            self.gc(61)

            winv = _ensure_dst_keyvect(None, rounds)
            for i in range(rounds):
                _invert(_tmp_bf_0, w.to(i))
                winv.read(i, _tmp_bf_0)
                self.gc(62)

            g_scalar = _ensure_dst_key()
            h_scalar = _ensure_dst_key()
            twoN = self._two_aux(N)
            for i in range(MN):
                _copy_key(g_scalar, proof.a)
                _sc_mul(h_scalar, proof.b, yinvpow)

                for j in range(rounds - 1, -1, -1):
                    J = len(w) - j - 1

                    if (i & (1 << j)) == 0:
                        _sc_mul(g_scalar, g_scalar, winv.to(J))
                        _sc_mul(h_scalar, h_scalar, w.to(J))
                    else:
                        _sc_mul(g_scalar, g_scalar, w.to(J))
                        _sc_mul(h_scalar, h_scalar, winv.to(J))

                # Adjust the scalars using the exponents from PAPER LINE 62
                _sc_add(g_scalar, g_scalar, z)
                utils.ensure(2 + i // N < len(zpow), "invalid zpow index")
                utils.ensure(i % N < len(twoN), "invalid twoN index")
                _sc_mul(tmp, zpow.to(2 + i // N), twoN.to(i % N))
                _sc_muladd(tmp, z, ypow, tmp)
                _sc_mulsub(h_scalar, tmp, yinvpow, h_scalar)

                if not is_single:  # ph4
                    m_z4.read(i, _sc_mulsub(_tmp_bf_0, g_scalar, weight_z, m_z4[i]))
                    m_z5.read(i, _sc_mulsub(_tmp_bf_0, h_scalar, weight_z, m_z5[i]))
                else:
                    _sc_mul(tmp, g_scalar, weight_z)
                    _sub_keys(
                        muex_acc, muex_acc, _scalarmult_key(tmp, Gprec.to(i), tmp)
                    )

                    _sc_mul(tmp, h_scalar, weight_z)
                    _sub_keys(
                        muex_acc, muex_acc, _scalarmult_key(tmp, Hprec.to(i), tmp)
                    )

                if i != MN - 1:
                    _sc_mul(yinvpow, yinvpow, yinv)
                    _sc_mul(ypow, ypow, y)
                if i & 15 == 0:
                    self.gc(62)

            del (g_scalar, h_scalar, twoN)
            self.gc(63)

            _sc_muladd(z1, proof.mu, weight_z, z1)
            muex = MultiExpSequential(
                point_fnc=lambda i, d: proof.L[i // 2]
                if i & 1 == 0
                else proof.R[i // 2]
            )
            for i in range(rounds):
                _sc_mul(tmp, w.to(i), w.to(i))
                _sc_mul(tmp, tmp, weight_z8)
                muex.add_scalar(tmp)
                _sc_mul(tmp, winv.to(i), winv.to(i))
                _sc_mul(tmp, tmp, weight_z8)
                muex.add_scalar(tmp)

            acc = _multiexp(None, muex, False)
            _add_keys(muex_acc, muex_acc, acc)

            _sc_mulsub(tmp, proof.a, proof.b, proof.t)
            _sc_mul(tmp, tmp, x_ip)
            _sc_muladd(z3, tmp, weight_z, z3)

        _sc_sub(tmp, m_y0, z1)
        z3p = _sc_sub(None, z3, y1)

        check2 = crypto.encodepoint(
            crypto.ge25519_double_scalarmult_base_vartime(
                crypto.decodeint(z3p), crypto.xmr_H(), crypto.decodeint(tmp)
            )
        )
        _add_keys(muex_acc, muex_acc, check2)

        if not is_single:  # ph4
            muex = MultiExpSequential(
                point_fnc=lambda i, d: Gprec.to(i // 2)
                if i & 1 == 0
                else Hprec.to(i // 2)
            )
            for i in range(maxMN):
                muex.add_scalar(m_z4[i])
                muex.add_scalar(m_z5[i])
            _add_keys(muex_acc, muex_acc, _multiexp(None, muex, True))

        if muex_acc != _ONE:
            raise ValueError("Verification failure at step 2")
        return True
