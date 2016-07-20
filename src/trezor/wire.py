import ustruct
import ubinascii
from . import msg
from . import loop
from . import log

IFACE = const(0)

# TREZOR wire protocol v2:
#
# HID report = 64 bytes, padded with 0x0
# First report = !SSSSTTTTLLLLD...
# Next reports = #SSSSD...CCCC
#
# S = session id
# T = message type
# L = data length
# D = data
# C = data checksum - crc32

_REPORT_LEN = const(64)
_MAX_DATA_LEN = const(65536)
_HEADER_MAGIC = const(35)  # ord('#')
_DATA_MAGIC = const(33)  # ord('!')


def _read_report():
    rep, = yield loop.Select(IFACE)
    assert len(rep) == _REPORT_LEN, 'HID read failed'
    return memoryview(rep)


def _write_report(rep):
    size = msg.send(IFACE, rep)
    assert size == _REPORT_LEN, 'HID write failed'
    yield  # just to be a generator


def read_wire_msg():

    rep = yield from _read_report()
    magic, sid, mtype, mlen = ustruct.unpack('>BLLL', rep)
    assert magic == _HEADER_MAGIC, 'Incorrect report magic'
    assert mlen < _MAX_DATA_LEN, 'Message too large to read'

    mlen += 4  # Account for the checksum
    data = rep[13:][:mlen]  # Skip magic and header, trim to data len
    remaining = mlen - len(data)
    buffered = bytearray(data) if remaining > 0 else data  # Avoid the copy if we don't append

    while remaining > 0:
        rep = yield from _read_report()
        magic, rsid = ustruct.unpack('>BL', rep)
        assert magic == _DATA_MAGIC, 'Incorrect report magic'
        assert rsid == sid, 'Session ID mismatch'

        data = rep[5:][:remaining]  # Skip magic and session ID, trim
        buffered.extend(data)
        remaining -= len(data)

    # Split to data and checksum
    mbuf = buffered[:-4]
    csum = ustruct.unpack_from('>L', buffered, -4)

    # Compare the checksums
    assert csum == ubinascii.crc32(mbuf), 'Message checksum mismatch'

    return sid, mtype, mbuf


def write_wire_msg(sid, mtype, mbuf):

    rep = bytearray(_REPORT_LEN)
    rep[0] = _HEADER_MAGIC
    ustruct.pack_into('>LLL', rep, 1, sid, mtype, len(mbuf))

    rep = memoryview(rep)
    mbuf = memoryview(mbuf)
    data = rep[13:]  # Skip magic and header

    csum = ubinascii.crc32(mbuf)
    footer = ustruct.pack('>L', csum)

    while True:
        n = min(len(data), len(mbuf))
        data[:n] = mbuf[:n]  # Copy as much data as possible from mbuf to data
        mbuf = mbuf[n:]  # Skip written bytes
        data = data[n:]  # Skip written bytes

        # Continue with the footer if mbuf is empty and we have space
        if not mbuf and data:
            mbuf = footer
            continue

        yield from _write_report(rep)
        if not mbuf:
            break

        # Reset to skip the magic and session ID
        data = rep[5:]


def read(*types):
    if __debug__:
        log.debug(__name__, 'Reading one of %s', types)
    _, mtype, mbuf = yield from read_wire_msg()
    for t in types:
        if t.wire_type == mtype:
            return t.loads(mbuf)
    else:
        raise Exception('Unexpected message')


def write(m):
    if __debug__:
        log.debug(__name__, 'Writing %s', m)
    mbuf = m.dumps()
    mtype = m.message_type.wire_type
    yield from write_wire_msg(0, mtype, mbuf)


def call(req, *types):
    yield from write(req)
    res = yield from read(*types)
    return res
