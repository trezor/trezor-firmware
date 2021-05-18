from c.storage import Storage as StorageC
from python.src import prng
from python.src.storage import Storage as StoragePy

test_uid = b"\x67\xce\x6a\xe8\xf7\x9b\x73\x96\x83\x88\x21\x5e"


def init(
    unlock: bool = False, reseed: int = 0, uid: int = test_uid
) -> (StorageC, StoragePy):
    sc = StorageC()
    sp = StoragePy()
    sc.lib.random_reseed(reseed)
    prng.random_reseed(reseed)
    for s in (sc, sp):
        s.init(uid)
        if unlock:
            assert s.unlock("")
    return sc, sp


def memory_equals(sc, sp) -> bool:
    return sc._dump() == sp._dump()
