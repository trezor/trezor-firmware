from ..src import consts, helpers


def test_read_bytes_by_words():
    array = b"\x04\x03\x02\x01\x08\x07\x06\x05"
    n = helpers.to_int_by_words(array)
    assert n == 0x0102030405060708
    assert array == helpers.to_bytes_by_words(n, consts.PIN_LOG_SIZE)[56:]

    array = b"\xFF\xFF\xFF\x01\x01\x05\x09\x01"
    n = helpers.to_int_by_words(array)
    assert n == 0x01FFFFFF01090501
    assert array == helpers.to_bytes_by_words(n, consts.PIN_LOG_SIZE)[56:]
