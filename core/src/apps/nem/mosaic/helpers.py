from .nem_mosaics import mosaics

if False:
    from typing import Any

    MosaicDict = dict[str, Any]


class Mosaic:
    # TODO: or we can create NEMMosaicDefinition object???
    def __init__(self, mosaic_dict: MosaicDict) -> None:
        self.name: str = mosaic_dict["name"]
        self.ticker: str = mosaic_dict["ticker"]
        self.namespace: str = mosaic_dict["namespace"]
        self.mosaic: str = mosaic_dict["mosaic"]
        self.divisibility: int = mosaic_dict["divisibility"]
        self.levy: str | None = mosaic_dict.get("levy")
        self.fee: int | None = mosaic_dict.get("fee")
        self.levy_namespace: str | None = mosaic_dict.get("levy_namespace")
        self.levy_mosaic: str | None = mosaic_dict.get("levy_mosaic")
        self.networks: list[int] | None = mosaic_dict.get("networks")


def get_mosaic_definition(
    namespace_name: str, mosaic_name: str, network: int
) -> Mosaic | None:
    for m in mosaics:
        mosaic = Mosaic(m)
        if namespace_name == mosaic.namespace and mosaic_name == mosaic.mosaic:
            if (mosaic.networks is None) or (network in mosaic.networks):
                return mosaic
    return None


def is_nem_xem_mosaic(namespace_name: str, mosaic_name: str) -> bool:
    if namespace_name == "nem" and mosaic_name == "xem":
        return True
    return False
