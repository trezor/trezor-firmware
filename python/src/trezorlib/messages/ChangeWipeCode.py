# Automatically generated by pb2py
# fmt: off
# isort:skip_file
from .. import protobuf as p

if __debug__:
    try:
        from typing import Dict, List, Optional  # noqa: F401
        from typing_extensions import Literal  # noqa: F401
    except ImportError:
        pass


class ChangeWipeCode(p.MessageType):
    MESSAGE_WIRE_TYPE = 82

    def __init__(
        self,
        *,
        remove: Optional[bool] = None,
    ) -> None:
        self.remove = remove

    @classmethod
    def get_fields(cls) -> Dict:
        return {
            1: ('remove', p.BoolType, None),
        }
