from ..src import pin_log, prng


def test_generate_guard_key():
    prng.random_reseed(0)

    p = pin_log.PinLog(None)

    assert p._generate_guard_key() == 2267428717
    assert p._generate_guard_key() == 1653399972
    assert p._check_guard_key(2267428717)
    assert p._check_guard_key(1653399972)
    assert p._check_guard_key(3706993061)
    assert p._check_guard_key(3593237286)
