from typing import TYPE_CHECKING

from .nem_mosaics import mosaics_iterator

if TYPE_CHECKING:
    from trezor.messages import NEMMosaic

    from .nem_mosaics import Mosaic


def get_mosaic_definition(
    namespace_name: str, mosaic_name: str, network: int
) -> Mosaic | None:
    for mosaic in mosaics_iterator():
        if namespace_name == mosaic.namespace and mosaic_name == mosaic.mosaic:
            if (mosaic.networks is None) or (network in mosaic.networks):
                return mosaic
    return None


def is_nem_xem_mosaic(mosaic: Mosaic | NEMMosaic) -> bool:
    if mosaic.namespace == "nem" and mosaic.mosaic == "xem":
        return True
    return False
