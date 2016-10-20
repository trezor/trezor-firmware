from ubinascii import hexlify
from micropython import const
from trezor import msg, loop, log

_DEFAULT_IFACE = const(0xFF00)  # TODO: use proper interface


def read_report_stream(target, iface=_DEFAULT_IFACE):
    while True:
        report, = yield loop.Select(iface)
        log.debug(__name__, 'read report %s', hexlify(report))
        target.send(memoryview(report))


def write_report_stream(iface=_DEFAULT_IFACE):
    while True:
        report = yield
        log.debug(__name__, 'write report %s', hexlify(report))
        msg.send(iface, report)
