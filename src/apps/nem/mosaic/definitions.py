# todo move to common and generate via script


def get_mosaic_definition(namespace_name: str, mosaic_name: str, network: int):
    for m in mosaics:
        if namespace_name == m["namespace"] and mosaic_name == m["mosaic"]:
            if ("networks" not in m) or (network in m["networks"]):
                return m
    return None


def is_nem_xem_mosaic(namespace_name: str, mosaic_name: str):
    if namespace_name == "nem" and mosaic_name == "xem":
        return True
    return False


mosaics = [
    {
        "name": "XEM",
        "ticker": " XEM",
        "namespace": "nem",
        "mosaic": "xem",
        "divisibility": 6
    },
    {
        "name": "DIMCOIN",
        "ticker": " DIM",
        "namespace": "dim",
        "mosaic": "coin",
        "divisibility": 6,
        "levy": "MosaicLevy_Percentile",
        "fee": 10,
        "levy_namespace": "dim",
        "levy_mosaic": "coin",
        "networks": [ 104 ]
    },
    {
        "name": "DIM TOKEN",
        "ticker": " DIMTOK",
        "namespace": "dim",
        "mosaic": "token",
        "divisibility": 6,
        "networks": [ 104 ]
    },
    {
        "name": "Breeze Token",
        "ticker": " BREEZE",
        "namespace": "breeze",
        "mosaic": "breeze-token",
        "divisibility": 0,
        "networks": [ 104 ]
    },
    {
        "name": "PacNEM Game Credits",
        "ticker": " PAC:HRT",
        "namespace": "pacnem",
        "mosaic": "heart",
        "divisibility": 0,
        "networks": [ 104 ]
    },
    {
        "name": "PacNEM Score Tokens",
        "ticker": " PAC:CHS",
        "namespace": "pacnem",
        "mosaic": "cheese",
        "divisibility": 6,
        "levy": "MosaicLevy_Percentile",
        "fee": 100,
        "levy_namespace": "nem",
        "levy_mosaic": "xem",
        "networks": [ 104 ]
    }
]
