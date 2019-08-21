from ..src import prng


def pytest_runtest_teardown(item):
    """
    Called after each test ran to reset the PRNG
    """
    prng.seed = 0
