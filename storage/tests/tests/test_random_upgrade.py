import hypothesis.strategies as st
from hypothesis import assume, settings
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from c0.storage import Storage as StorageC0
from c.storage import Storage as StorageC

from . import common
from .storage_model import StorageModel


class StorageUpgrade(RuleBasedStateMachine):
    def __init__(self):
        super(StorageUpgrade, self).__init__()
        self.sc = StorageC0()
        self.sc.init()
        self.sm = StorageModel()
        self.sm.init(common.test_uid)
        self.storages = (self.sc, self.sm)
        self.ensure_unlocked()

    keys = Bundle("keys")
    values = Bundle("values")
    pins = Bundle("pins")

    @rule(target=keys, app=st.integers(1, 0xFF), key=st.integers(0, 0xFF))
    def k(self, app, key):
        return (app << 8) | key

    @rule(target=values, v=st.binary(min_size=0, max_size=10000))
    def v(self, v):
        return v

    @rule(target=pins, p=st.integers(1, 3))
    def p(self, p):
        return p

    @rule(k=keys, v=values)
    def set(self, k, v):
        assume(k != 0xFFFF)
        for s in self.storages:
            s.set(k, v)

    @rule(p=pins)
    def check_pin(self, p):
        assert self.sm.unlock(p) == self.sc.check_pin(p)
        self.ensure_unlocked()

    @rule(oldpin=pins, newpin=pins)
    def change_pin(self, oldpin, newpin):
        assert self.sm.change_pin(oldpin, newpin) == self.sc.change_pin(oldpin, newpin)
        self.ensure_unlocked()

    @invariant()
    def check_upgrade(self):
        sc1 = StorageC()
        sc1._set_flash_buffer(self.sc._get_flash_buffer())
        sc1.init(common.test_uid)
        assert self.sm.get_pin_rem() == sc1.get_pin_rem()
        assert sc1.unlock(self.sm.pin)
        for k, v in self.sm:
            assert sc1.get(k) == v

    def ensure_unlocked(self):
        if not self.sm.unlocked:
            for s in self.storages:
                assert s.unlock(self.sm.pin)


TestStorageUpgrade = StorageUpgrade.TestCase
TestStorageUpgrade.settings = settings(
    deadline=None, max_examples=30, stateful_step_count=50
)
