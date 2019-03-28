import struct

EVENT_TYPE_START = 2
EVENT_TYPE_STOP = 3
EVENT_TYPE_OPEN = 4
EVENT_TYPE_CLOSE = 5
EVENT_TYPE_OUTPUT = 6
EVENT_TYPE_CREATE2 = 11
EVENT_TYPE_INTPUT2 = 12

DATA_MAX = 4096
EVENT_LENGTH = 4380

INPUT2_REQ_FMT = "< H {}s".format(DATA_MAX)
CREATE2_REQ_FMT = "< 128s 64s 64s H H L L L L {}s".format(DATA_MAX)
START_REQ_FMT = "< Q"
OUTPUT_REQ_FMT = "< {}s H B".format(DATA_MAX)


def pack_event(ev_type, request):
    return ev_type.to_bytes(4, byteorder="little") + request


def unpack_event(buf):
    return int.from_bytes(buf[:4], byteorder="little"), buf[4:]


def parse_event(event):
    assert len(event) == EVENT_LENGTH

    ev_type, request = unpack_event(event)

    if ev_type == EVENT_TYPE_START:
        request = struct.unpack_from(START_REQ_FMT, request)
    elif ev_type == EVENT_TYPE_STOP:
        request = []
    elif ev_type == EVENT_TYPE_OPEN:
        request = []
    elif ev_type == EVENT_TYPE_CLOSE:
        request = []
    elif ev_type == EVENT_TYPE_OUTPUT:
        data, size, rtype = struct.unpack_from(OUTPUT_REQ_FMT, request)
        data = data[:size]
        request = [data, size, rtype]

    return ev_type, request


def create_create2_event(
    name, phys, uniq, bus, vendor, product, version, country, rd_data
):
    uhid_create2_req = struct.pack(
        CREATE2_REQ_FMT,
        name,
        phys,
        uniq,
        len(rd_data),
        bus,
        vendor,
        product,
        version,
        country,
        rd_data,
    )
    event = pack_event(EVENT_TYPE_CREATE2, uhid_create2_req)

    return event


def create_input2_event(data):
    uhid_input2_req = struct.pack(INPUT2_REQ_FMT, len(data), data)
    event = pack_event(EVENT_TYPE_INTPUT2, uhid_input2_req)
    return event
