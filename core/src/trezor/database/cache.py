from typing import Dict, Optional

from storage import cache

# TODO: implement cache pruning


def get(key: str) -> Optional[str]:
    data = cache.get(cache.APP_COMMON_DATABASE)
    if data is None:
        return None
    dictionary = deserialize(data)
    return dictionary.get(key, None)


def set(key: str, value: Optional[str]):
    data = cache.get(cache.APP_COMMON_DATABASE)
    if data is None:
        dictionary = {}
    else:
        dictionary = deserialize(data)
    dictionary[key] = value
    cache.set(cache.APP_COMMON_DATABASE, serialize(dictionary))


def delete(key: str):
    data = cache.get(cache.APP_COMMON_DATABASE)
    if data is None:
        return
    dictionary = deserialize(data)
    del dictionary[key]
    cache.set(cache.APP_COMMON_DATABASE, serialize(dictionary))


def wipe():
    cache.set(cache.APP_COMMON_DATABASE, b"")


def serialize(dictionary: Dict[str, Optional[str]]) -> bytes:
    data: bytes = b""
    for key, value in dictionary.items():
        data += len(key).to_bytes(4, "big")
        data += key.encode()
        if value is None:
            data += bytes([0x00])
        else:
            data += bytes([0x01])
            data += len(value).to_bytes(4, "big")
            data += value.encode()
    return data


def deserialize(data: bytes) -> Dict[str, Optional[str]]:
    dictionary = {}
    offset = 0
    while offset < len(data):
        key_length = int.from_bytes(data[offset : offset + 4], "big")
        offset += 4
        key = data[offset : offset + key_length].decode()
        offset += key_length
        if data[offset] == 0x00:
            value = None
            offset += 1
        else:
            offset += 1
            value_length = int.from_bytes(data[offset : offset + 4], "big")
            offset += 4
            value = data[offset : offset + value_length].decode()
            offset += value_length
        dictionary[key] = value
    return dictionary
