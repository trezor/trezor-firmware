from trezor import msg
from trezor import loop

_DEFAULT_IFACE = const(0)


def read_report_stream(target, iface=_DEFAULT_IFACE):
    while True:
        report, = yield loop.Select(iface)
        target.send(report)


def write_report_stream(iface=_DEFAULT_IFACE):
    while True:
        report = yield
        msg.send(iface, report)
