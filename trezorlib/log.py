import logging
from typing import Set, Type, Optional

from . import protobuf

OMITTED_MESSAGES = set()  # type: Set[Type[protobuf.MessageType]]


class PrettyProtobufFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        time = self.formatTime(record)
        message = '[{time}] {source} {level}: {msg}'.format(
            time=time, level=record.levelname.upper(),
            source=record.name,
            msg=super().format(record))
        if hasattr(record, 'protobuf'):
            if type(record.protobuf) in OMITTED_MESSAGES:
                message += " ({} bytes)".format(record.protobuf.ByteSize())
            else:
                message += "\n" + protobuf.format_message(record.protobuf)
        return message


def enable_debug_output(handler: Optional[logging.Handler] = None):
    if handler is None:
        handler = logging.StreamHandler()

    formatter = PrettyProtobufFormatter()
    handler.setFormatter(formatter)

    logger = logging.getLogger('trezorlib')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
