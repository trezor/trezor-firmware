import pytest

from python.src import consts
from python.src.norcow import NC_CLASSES

from . import common

# Strings for testing ChaCha20 encryption.
chacha_strings = [
    b"Short string.",
    b"",
    b"Although ChaCha20 is a stream cipher, it operates on blocks of 64 bytes. This string is over 152 bytes in length so that we test multi-block encryption.",
    b"This string is exactly 64 bytes long, that is exactly one block.",
]


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_delete(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        s.set(0xFF04, b"0123456789A")
        s.delete(0xFF04)
        s.set(0xFF04, b"0123456789AB")
        s.delete(0xFF04)
        s.set(0xFF04, b"0123456789ABC")
        s.delete(0xFF04)
    assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_equal(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        s.set(0xFF04, b"0123456789A")
        s.set(0xFF04, b"0123456789A")
        s.set(0xFF04, b"0123456789AB")
        s.set(0xFF04, b"0123456789AB")
        s.set(0xFF04, b"0123456789ABC")
        s.set(0xFF04, b"0123456789ABC")
        s.set(0xFF04, b"0123456789ABCDE")
        s.set(0xFF04, b"0123456789ABCDE")
        s.set(0xFF04, b"0123456789ABCDEF")
        s.set(0xFF04, b"0123456789ABCDEF")
    assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_over_ff(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        s.set(0xFF01, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF")
        s.set(0xFF01, b"0123456789A")
        s.set(0xFF02, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF")
        s.set(0xFF02, b"0123456789AB")
        s.set(0xFF03, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF")
        s.set(0xFF03, b"0123456789ABC")
        s.set(0xFF04, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF")
        s.set(0xFF04, b"0123456789ABCD")
        s.set(0xFF05, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF")
        s.set(0xFF05, b"0123456789ABCDE")
        s.set(
            0xFF06, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF"
        )
        s.set(0xFF06, b"0123456789ABCDEF")

    assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_get(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        s.set(0xBEEF, b"Hello")
        s.set(0xCAFE, b"world!  ")
        s.set(0xDEAD, b"How\n")
        s.set(0xAAAA, b"are")
        s.set(0x0901, b"you?")
        s.set(0x0902, b"Lorem")
        s.set(0x0903, b"ipsum")
        s.set(0xDEAD, b"A\n")
        s.set(0xDEAD, b"AAAAAAAAAAA")
        s.set(0x2200, b"BBBB")
    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        s.change_pin("", "222")
        s.change_pin("222", "99")
        s.set(0xAAAA, b"something else")
    assert common.memory_equals(sc, sp)

    # check data are not changed by gets
    datasc = sc._dump()
    datasp = sp._dump()

    for s in (sc, sp):
        assert s.get(0xAAAA) == b"something else"
        assert s.get(0x0901) == b"you?"
        assert s.get(0x0902) == b"Lorem"
        assert s.get(0x0903) == b"ipsum"
        assert s.get(0xDEAD) == b"AAAAAAAAAAA"
        assert s.get(0x2200) == b"BBBB"

    assert datasc == sc._dump()
    assert datasp == sp._dump()

    # test locked storage
    for s in (sc, sp):
        s.lock()
        with pytest.raises(RuntimeError):
            s.set(0xAAAA, b"test public")
        with pytest.raises(RuntimeError):
            s.set(0x0901, b"test protected")
        with pytest.raises(RuntimeError):
            s.get(0x0901)
        assert s.get(0xAAAA) == b"something else"

    # check that storage functions after unlock
    for s in (sc, sp):
        s.unlock("99")
        s.set(0xAAAA, b"public")
        s.set(0x0902, b"protected")
        assert s.get(0xAAAA) == b"public"
        assert s.get(0x0902) == b"protected"

    # test delete
    for s in (sc, sp):
        assert s.delete(0x0902)
    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        assert not s.delete(0x7777)
        assert not s.delete(0x0902)
    assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_get_all_len(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        for i in range(0, 133):
            data = bytes([(i + j) % 256 for j in range(0, i)])
            s.set(0xFF01 + i, data)
            assert s.get(0xFF01 + i) == data
    assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_get_all_len_enc(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        for i in range(0, 133):
            data = bytes([(i + j) % 256 for j in range(0, i)])
            s.set(0x101 + i, data)
            assert s.get(0x101 + i) == data
    assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_invalid_key(nc_class):
    for s in common.init(nc_class, unlock=True):
        with pytest.raises(RuntimeError):
            s.set(0xFFFF, b"Hello")


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_non_existing_key(nc_class):
    sc, sp = common.init(nc_class)
    for s in (sc, sp):
        with pytest.raises(RuntimeError):
            s.get(0xABCD)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_chacha_strings(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        for i, string in enumerate(chacha_strings):
            s.set(0x0301 + i, string)
    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        for i, string in enumerate(chacha_strings):
            assert s.get(0x0301 + i) == string


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_repeated(nc_class):
    test_strings = [[0x0501, b""], [0x0502, b"test"], [0x8501, b""], [0x8502, b"test"]]

    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        for key, val in test_strings:
            s.set(key, val)
            s.set(key, val)

    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        for key, val in test_strings:
            s.set(key, val)
    assert common.memory_equals(sc, sp)

    for key, val in test_strings:
        for s in (sc, sp):
            assert s.delete(key)
        assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_similar(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        s.set(0xBEEF, b"Satoshi")
        s.set(0xBEEF, b"satoshi")
    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        s.wipe()
        s.unlock("")
        s.set(0xBEEF, b"satoshi")
        s.set(0xBEEF, b"Satoshi")
    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        s.wipe()
        s.unlock("")
        s.set(0xBEEF, b"satoshi")
        s.set(0xBEEF, b"Satoshi")
        s.set(0xBEEF, b"Satoshi")
        s.set(0xBEEF, b"SatosHi")
        s.set(0xBEEF, b"satoshi")
        s.set(0xBEEF, b"satoshi\x00")
    assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_locked(nc_class):
    sc, sp = common.init(nc_class)
    for s in (sc, sp):
        s.lock()
        with pytest.raises(RuntimeError):
            s.set(0x0303, b"test")
        with pytest.raises(RuntimeError):
            s.set(0x8003, b"test")
    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        s.set(0xC001, b"Ahoj")
        s.set(0xC003, b"test")
    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        assert s.get(0xC001) == b"Ahoj"
        assert s.get(0xC003) == b"test"


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_counter(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for i in range(0, 200):
        for s in (sc, sp):
            assert i == s.next_counter(0xC001)
        assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        s.lock()
        s.set_counter(0xC001, 500)
    assert common.memory_equals(sc, sp)

    for i in range(501, 700):
        for s in (sc, sp):
            assert i == s.next_counter(0xC001)
    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        with pytest.raises(RuntimeError):
            s.set_counter(0xC001, consts.UINT32_MAX + 1)

        start = consts.UINT32_MAX - 100
        s.set_counter(0xC001, start)
        for i in range(start, consts.UINT32_MAX):
            assert i + 1 == s.next_counter(0xC001)

        with pytest.raises(RuntimeError):
            s.next_counter(0xC001)

    assert common.memory_equals(sc, sp)
