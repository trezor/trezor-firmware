from .nem_mosaics import mosaics


def get_mosaic_definition(namespace_name: str, mosaic_name: str, network: int) -> dict:
    for m in mosaics:
        if namespace_name == m["namespace"] and mosaic_name == m["mosaic"]:
            if ("networks" not in m) or (network in m["networks"]):
                return m
    return None


def is_nem_xem_mosaic(namespace_name: str, mosaic_name: str) -> bool:
    if namespace_name == "nem" and mosaic_name == "xem":
        return True
    return False
