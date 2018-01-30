# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

'''
Extremely minimal streaming codec for a subset of protobuf.  Supports uint32,
bytes, string, embedded message and repeated fields.

For de-sererializing (loading) protobuf types, object with `Reader`
interface is required:

>>> class Reader:
>>>     def readinto(self, buffer):
>>>         """
>>>         Reads `len(buffer)` bytes into `buffer`, or raises `EOFError`.
>>>         """

For serializing (dumping) protobuf types, object with `Writer` interface is
required:

>>> class Writer:
>>>     def write(self, buffer):
>>>         """
>>>         Writes all bytes from `buffer`, or raises `EOFError`.
>>>         """
'''

from io import BytesIO

_UVARINT_BUFFER = bytearray(1)


def load_uvarint(reader):
    buffer = _UVARINT_BUFFER
    result = 0
    shift = 0
    byte = 0x80
    while byte & 0x80:
        if reader.readinto(buffer) == 0:
            raise EOFError
        byte = buffer[0]
        result += (byte & 0x7F) << shift
        shift += 7
    return result


def dump_uvarint(writer, n):
    buffer = _UVARINT_BUFFER
    shifted = True
    while shifted:
        shifted = n >> 7
        buffer[0] = (n & 0x7F) | (0x80 if shifted else 0x00)
        writer.write(buffer)
        n = shifted


class UVarintType:
    WIRE_TYPE = 0


class Sint32Type:
    WIRE_TYPE = 0


class Sint64Type:
    WIRE_TYPE = 0


class BoolType:
    WIRE_TYPE = 0


class BytesType:
    WIRE_TYPE = 2


class UnicodeType:
    WIRE_TYPE = 2


class MessageType:
    WIRE_TYPE = 2
    FIELDS = {}

    def __init__(self, **kwargs):
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])
        self._fill_missing()

    def __eq__(self, rhs):
        return (self.__class__ is rhs.__class__ and
                self.__dict__ == rhs.__dict__)

    def __repr__(self):
        d = {}
        for key, value in self.__dict__.items():
            if value is None or value == []:
                continue
            d[key] = value
        return '<%s: %s>' % (self.__class__.__name__, d)

    def __iter__(self):
        return self.__dict__.__iter__()

    def __getattr__(self, attr):
        if attr.startswith('_add_'):
            return self._additem(attr[5:])

        if attr.startswith('_extend_'):
            return self._extenditem(attr[8:])

        raise AttributeError(attr)

    def _extenditem(self, attr):
        def f(param):
            try:
                l = getattr(self, attr)
            except AttributeError:
                l = []
                setattr(self, attr, l)

            l += param

        return f

    def _additem(self, attr):
        # Add new item for repeated field type
        for v in self.FIELDS.values():
            if v[0] != attr:
                continue
            if not (v[2] & FLAG_REPEATED):
                raise AttributeError

            try:
                l = getattr(self, v[0])
            except AttributeError:
                l = []
                setattr(self, v[0], l)

            item = v[1]()
            l.append(item)
            return lambda: item

        raise AttributeError

    def _fill_missing(self):
        # fill missing fields
        for fname, ftype, fflags in self.FIELDS.values():
            if not hasattr(self, fname):
                if fflags & FLAG_REPEATED:
                    setattr(self, fname, [])
                else:
                    setattr(self, fname, None)

    def CopyFrom(self, obj):
        self.__dict__ = obj.__dict__.copy()

    def ByteSize(self):
        data = BytesIO()
        dump_message(data, self)
        return len(data.getvalue())


class LimitedReader:

    def __init__(self, reader, limit):
        self.reader = reader
        self.limit = limit

    def readinto(self, buf):
        if self.limit < len(buf):
            raise EOFError
        else:
            nread = self.reader.readinto(buf)
            self.limit -= nread
            return nread


class CountingWriter:

    def __init__(self):
        self.size = 0

    def write(self, buf):
        nwritten = len(buf)
        self.size += nwritten
        return nwritten


FLAG_REPEATED = 1


def load_message(reader, msg_type):
    fields = msg_type.FIELDS
    msg = msg_type()

    while True:
        try:
            fkey = load_uvarint(reader)
        except EOFError:
            break  # no more fields to load

        ftag = fkey >> 3
        wtype = fkey & 7

        field = fields.get(ftag, None)

        if field is None:  # unknown field, skip it
            if wtype == 0:
                load_uvarint(reader)
            elif wtype == 2:
                ivalue = load_uvarint(reader)
                reader.readinto(bytearray(ivalue))
            else:
                raise ValueError
            continue

        fname, ftype, fflags = field
        if wtype != ftype.WIRE_TYPE:
            raise TypeError  # parsed wire type differs from the schema

        ivalue = load_uvarint(reader)

        if ftype is UVarintType:
            fvalue = ivalue
        elif ftype is Sint32Type:
            fvalue = (ivalue >> 1) ^ ((ivalue << 31) & 0xffffffff)
        elif ftype is Sint64Type:
            fvalue = (ivalue >> 1) ^ ((ivalue << 63) & 0xffffffffffffffff)
        elif ftype is BoolType:
            fvalue = bool(ivalue)
        elif ftype is BytesType:
            fvalue = bytearray(ivalue)
            reader.readinto(fvalue)
        elif ftype is UnicodeType:
            fvalue = bytearray(ivalue)
            reader.readinto(fvalue)
            fvalue = fvalue.decode()
        elif issubclass(ftype, MessageType):
            fvalue = load_message(LimitedReader(reader, ivalue), ftype)
        else:
            raise TypeError  # field type is unknown

        if fflags & FLAG_REPEATED:
            pvalue = getattr(msg, fname)
            pvalue.append(fvalue)
            fvalue = pvalue
        setattr(msg, fname, fvalue)

    return msg


def dump_message(writer, msg):
    repvalue = [0]
    mtype = msg.__class__
    fields = mtype.FIELDS

    for ftag in fields:
        field = fields[ftag]
        fname = field[0]
        ftype = field[1]
        fflags = field[2]

        fvalue = getattr(msg, fname, None)
        if fvalue is None:
            continue

        fkey = (ftag << 3) | ftype.WIRE_TYPE

        if not fflags & FLAG_REPEATED:
            repvalue[0] = fvalue
            fvalue = repvalue

        for svalue in fvalue:
            dump_uvarint(writer, fkey)

            if ftype is UVarintType:
                dump_uvarint(writer, svalue)

            elif ftype is Sint32Type:
                dump_uvarint(writer, ((svalue << 1) & 0xffffffff) ^ (svalue >> 31))

            elif ftype is Sint64Type:
                dump_uvarint(writer, ((svalue << 1) & 0xffffffffffffffff) ^ (svalue >> 63))

            elif ftype is BoolType:
                dump_uvarint(writer, int(svalue))

            elif ftype is BytesType:
                dump_uvarint(writer, len(svalue))
                writer.write(svalue)

            elif ftype is UnicodeType:
                if not isinstance(svalue, bytes):
                    svalue = svalue.encode('utf-8')

                dump_uvarint(writer, len(svalue))
                writer.write(svalue)

            elif issubclass(ftype, MessageType):
                counter = CountingWriter()
                dump_message(counter, svalue)
                dump_uvarint(writer, counter.size)
                dump_message(writer, svalue)

            else:
                raise TypeError
