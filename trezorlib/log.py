import logging
from typing import Set, Type

from . import protobuf

OMITTED_MESSAGES = set()  # type: Set[Type[protobuf.MessageType]]


class PrettyProtobufFormatter(logging.Formatter):

    def format(self, record):
        time = self.formatTime(record)
        message = '[{time}] {level}: {msg}'.format(time=time, level=record.levelname, msg=super().format(record))
        if hasattr(record, 'protobuf'):
            if type(record.protobuf) in OMITTED_MESSAGES:
                message += " ({} bytes)".format(record.protobuf.ByteSize())
            else:
                message += "\n" + protobuf.format_message(record.protobuf)
        return message
