import hypothesis.strategies as st
from hypothesis import assume, settings
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from . import common
from .storage_model import StorageModel


class StorageComparison(RuleBasedStateMachine):
    def __init__(self):
        super(StorageComparison, self).__init__()
        self.sc, self.sp = common.init(unlock=True)
        self.sm = StorageModel()
        self.sm.init(b"")
        self.sm.unlock("")
        self.storages = (self.sc, self.sp, self.sm)

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
        if p == 1:
            return ""
        else:
            return str(p)

    @rule(k=keys, v=values)
    def set(self, k, v):
        assume(k != 0xFFFF)
        for s in self.storages:
            s.set(k, v)

    @rule(k=keys)
    def delete(self, k):
        assume(k != 0xFFFF)
        assert len(set(s.delete(k) for s in self.storages)) == 1

    @rule(p=pins)
    def check_pin(self, p):
        assert len(set(s.unlock(p) for s in self.storages)) == 1
        self.ensure_unlocked()

    @rule(oldpin=pins, newpin=pins)
    def change_pin(self, oldpin, newpin):
        assert len(set(s.change_pin(oldpin, newpin) for s in self.storages)) == 1
        self.ensure_unlocked()

    @rule()
    def lock(self):
        for s in self.storages:
            s.lock()
        self.ensure_unlocked()

    @invariant()
    def values_agree(self):
        for k, v in self.sm:
            assert self.sc.get(k) == v

    @invariant()
    def dumps_agree(self):
        assert self.sc._dump() == self.sp._dump()

    @invariant()
    def pin_counters_agree(self):
        assert len(set(s.get_pin_rem() for s in self.storages)) == 1

    def ensure_unlocked(self):
        if not self.sm.unlocked:
            for s in self.storages:
                assert s.unlock(self.sm.pin)


TestStorageComparison = StorageComparison.TestCase
TestStorageComparison.settings = settings(
    deadline=2000, max_examples=30, stateful_step_count=50
)
