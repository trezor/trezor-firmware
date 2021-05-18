import pytest

from python.src import consts

from . import common

# Strings for testing ChaCha20 encryption.
chacha_strings = [
    b"Short string.",
    b"",
    b"Although ChaCha20 is a stream cipher, it operates on blocks of 64 bytes. This string is over 152 bytes in length so that we test multi-block encryption.",
    b"This string is exactly 64 bytes long, that is exactly one block.",
]


def test_set_get():
    sc, sp = common.init(unlock=True)
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


def test_invalid_key():
    for s in common.init(unlock=True):
        with pytest.raises(RuntimeError):
            s.set(0xFFFF, b"Hello")


def test_non_existing_key():
    sc, sp = common.init()
    for s in (sc, sp):
        with pytest.raises(RuntimeError):
            s.get(0xABCD)


def test_chacha_strings():
    sc, sp = common.init(unlock=True)
    for s in (sc, sp):
        for i, string in enumerate(chacha_strings):
            s.set(0x0301 + i, string)
    assert common.memory_equals(sc, sp)

    for s in (sc, sp):
        for i, string in enumerate(chacha_strings):
            assert s.get(0x0301 + i) == string


def test_set_repeated():
    test_strings = [[0x0501, b""], [0x0502, b"test"], [0x8501, b""], [0x8502, b"test"]]
    sc, sp = common.init(unlock=True)
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


def test_set_similar():
    sc, sp = common.init(unlock=True)
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


def test_set_locked():
    sc, sp = common.init()
    for s in (sc, sp):
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
        s.get(0xC001) == b"Ahoj"
        s.get(0xC003) == b"test"


def test_counter():
    sc, sp = common.init(unlock=True)
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
