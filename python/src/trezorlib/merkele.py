from binascii import hexlify, unhexlify
from hashlib import sha256

TEST_PRINT = True


class App:
    app_hash: bytes

    name: str
    data_hash: bytes
    data_size: int
    data: bytes

    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self.data = data

        self.data_size = len(data)
        self.data_hash = sha256(data).digest()

        app_hash_ctx = sha256(name.encode())
        app_hash_ctx.update(self.data_size.to_bytes(4, "big"))
        app_hash_ctx.update(self.data_hash)
        self.app_hash = app_hash_ctx.digest()

    def format(self) -> str:
        return "\n".join(
            [
                self.name,
                str(hexlify(self.app_hash)),
                str(hexlify(self.data)),
                "",
            ]
        )


def _get_apps() -> list[App]:
    app_vector = {
        ("1_ first app", "DEADBEEF"),
        ("2_ second app", "11111111111122222222"),
        ("3_ third app", "0123"),
        ("4_ fourth app", "2233445566778899"),
        ("5_ fifth app", "aabbccddeeffaa00112233112332"),
    }
    apps: list[App] = []
    for name, data_hex in app_vector:
        apps.append(App(name=name, data=unhexlify(data_hex)))
    apps.sort(key=lambda app: app.name)
    return apps


def create_tree(apps: list[App]) -> list:
    internal_node_count = len(apps) - 1
    ret: list[bytes] = [b""] * (internal_node_count)
    for app in apps:
        ret.append(app.app_hash)
    for i in range(internal_node_count):
        x = internal_node_count - i - 1
        val = sha256(ret[2 * x + 1] + ret[2 * x + 2]).digest()
        ret[x] = (
            i.to_bytes(1, "big")
            + b"\x00"
            + (2 * x + 1).to_bytes(1, "big")
            + (2 * x + 2).to_bytes(1, "big")
            + b"\x00"
            + val
        )

    return ret


def get_path(n: int) -> list[int]:
    idx = n
    ret: list[int] = []
    while idx > 0:
        if idx % 2 == 0:
            ret.append(idx - 1)
        else:
            ret.append(idx + 1)
        idx = (idx - 1) // 2
        ret.append(idx)
    return ret


apps: list[App] = _get_apps()

if TEST_PRINT:
    # for app in apps:
    #     print(app.format())

    for app in apps:
        print(f"hash:{hexlify(app.app_hash)}, name: {app.name}")
    print("\n")
    tree = create_tree(apps)
    for i, node in enumerate(tree):
        print(i, hexlify(node or b""))
    print("\n")
    for i in range(1, 9):
        path = get_path(i)
        print(f"{i}: {' '.join([str(p) for p in path])}")
