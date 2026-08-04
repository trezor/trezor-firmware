from trezor.messages import ExtAppMessage, ExtAppResponse
from trezor.wire.errors import DataError


async def run(_request: ExtAppMessage) -> ExtAppResponse:
    raise DataError("Not implemented")
