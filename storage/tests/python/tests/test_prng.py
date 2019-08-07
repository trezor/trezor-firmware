from ..src import prng


def test_prng():
    prng.random_reseed(0)

    buf = prng.random_buffer(4)
    assert buf == b"\x5f\xf3\x6e\x3c"
    buf = prng.random_buffer(4)
    assert buf == b"\x32\x29\x50\x47"

    buf = prng.random_buffer(8)
    assert buf == b"\xe9\xf6\xcc\xd1\x34\x53\xf9\xaa"
