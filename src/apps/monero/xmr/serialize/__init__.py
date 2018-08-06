import gc


def parse_msg(buf: bytes, msg_type):
    from apps.monero.xmr.serialize.readwriter import MemoryReaderWriter

    reader = MemoryReaderWriter(memoryview(buf))
    return msg_type.load(reader)


def dump_msg(msg, preallocate: int = None, prefix: bytes = None) -> bytes:
    from apps.monero.xmr.serialize.readwriter import MemoryReaderWriter

    writer = MemoryReaderWriter(preallocate=preallocate)
    if prefix:
        writer.write(prefix)
    msg_type = msg.__class__
    msg_type.dump(writer, msg)

    return writer.get_buffer()


def dump_msg_gc(msg, preallocate: int = None, prefix: bytes = None) -> bytes:
    buf = dump_msg(msg, preallocate, prefix)
    del msg
    gc.collect()
    return buf
