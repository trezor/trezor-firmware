'''PipeTransport implements fake wire transport over local named pipe.
Use this transport for talking with trezor simulator.'''

import os
import ustruct
import uselect

from trezor import loop

read_fd = None
write_fd = None

poll = None
on_read = None

def init(filename):
    global read_fd, write_fd, poll

    filename_read = filename + '.to'
    filename_write = filename + '.from'

    os.mkfifo(filename_read, 0o600)
    os.mkfifo(filename_write, 0o600)

    write_fd = os.open(filename_write, os.O_RDWR, 0o600)
    read_fd = os.open(filename_read, os.O_RDWR, 0o600)

    poll = uselect.poll()
    poll.register(read_fd, uselect.POLLIN)

    # Setup polling
    loop.call_soon(watch_read())

def set_notify(_on_read):
    global on_read
    on_read = _on_read

def close():
    global read_fd, write_fd

    os.close(read_fd)
    os.close(write_fd)

def watch_read():
    global on_read
    sleep = loop.Sleep(10000)  # 0.01s
    while True:
        if ready_to_read() and on_read:
            on_read()

        yield sleep

def ready_to_read():
    global poll
    return len(poll.poll(0)) > 0

def read():
    """
    If there is data available to be read from the transport, reads the data and tries to parse it as a protobuf message.  If the parsing succeeds, return a protobuf object.
    Otherwise, returns None.
    """

    if not ready_to_read():
        return None

    data = _read()
    if data == None:
        return None

    return _parse_message(data)

def write(msg):
    """
    Write mesage to tansport.  msg should be a member of a valid `protobuf class <https://developers.google.com/protocol-buffers/docs/pythontutorial>`_ with a SerializeToString() method.
    """
    ser = msg.SerializeToString()
    header = ustruct.pack(">HL", mapping.get_type(msg), len(ser))

    _write(b"##%s%s" % (header, ser))

def _parse_message(data):
    (msg_type, _data) = data
    if msg_type == 'protobuf':
        return _data
    else:
        # inst = mapping.get_class(msg_type)()
        # inst.ParseFromString(_data)
        inst = _data
        return inst

def _read_headers():
    global read_fd

    # Try to read headers until some sane value are detected
    is_ok = False
    while not is_ok:

        # Align cursor to the beginning of the header ("##")
        c = os.read(read_fd, 1)
        i = 0
        while c != b'#':
            i += 1
            if i >= 64:
                # timeout
                raise Exception("Timed out while waiting for the magic character")
            # print "Aligning to magic characters"
            c = os.read(read_fd, 1)
            print(c)

        if os.read(read_fd, 1) != b'#':
            # Second character must be # to be valid header
            raise Exception("Second magic character is broken")

        # Now we're most likely on the beginning of the header
        try:
            headerlen = ustruct.calcsize(">HL")
            (msg_type, datalen) = ustruct.unpack(">HL", os.read(read_fd, headerlen))
            break
        except:
            raise Exception("Cannot parse header length")

    return (msg_type, datalen)

def _write(msg):
    global write_fd
    try:
        os.write(write_fd, msg)
        # os.fsync(write_fd)
    except OSError:
        print("Error while writing to socket")
        raise

def _read():
    global read_fd
    try:
        (msg_type, datalen) = _read_headers()
        return (msg_type, os.read(read_fd, datalen))
    except:
        print("Failed to read from device")
        raise
