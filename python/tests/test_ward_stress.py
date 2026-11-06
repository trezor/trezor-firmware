"""Coverage oracle and fail-fast behavior for the real-device stress runner."""

from itertools import product

import pytest

from trezorlib._internal.ward_stress import (
    OPERATIONS,
    expected_coverage,
    run_extra_long,
)


def test_graph_coverage_matches_literal_short_sequences():
    brute_force = set()
    for sequence in product(OPERATIONS, repeat=3):
        state = [None, None]
        for depth, operation in enumerate(sequence, 1):
            brute_force.add((depth, tuple(state), operation.name))
            if operation.method == "delete":
                state[operation.key] = None
            elif operation.method == "write":
                state[operation.key] = operation.value
    assert expected_coverage(3) == brute_force


class DeviceModel:
    def __init__(self):
        self.values = {}
        self.counter = 0
        self.events = []
        self.displays = 0

    def call(self, method, params):
        address = params.get("address")
        if method == "lookup":
            return {
                "wardId": "wallet",
                "counter": self.counter,
                "valid": True,
                "isMember": address in self.values,
            }
        if method == "update":
            if params.get("delete"):
                if address in self.values:
                    del self.values[address]
                    self.counter += 1
            else:
                self.values[address] = params.get("metadata", {}).get("label", "")
                self.counter += 1
        return {
            "wardId": "wallet",
            "counter": self.counter,
            "root": str(self.counter) if self.values else "",
        }

    def display(self, params, label):
        assert self.values[params["address"]] == label
        self.displays += 1

    def run(self, depth=10):
        return run_extra_long(
            self.call,
            lambda operation: operation(),
            self.display,
            self.events.append,
            "test",
            max_depth=depth,
        )


def test_depth_ten_covers_every_reachable_edge_and_restores_empty_state():
    device = DeviceModel()
    summary = device.run()
    covered = {
        (event["depth"], tuple(event["before"]), event["operation"])
        for event in device.events
        if event.get("phase") == "coverage"
    }
    assert covered == expected_coverage(10)
    assert summary["coveredEdges"] == summary["expectedEdges"] == 702
    assert summary["maxDepth"] == 10
    assert device.values == {}
    assert device.displays > 0
    assert device.counter > 10  # Restores retain the real monotonic history.


@pytest.mark.parametrize("depth", [0, 11])
def test_depth_is_bounded(depth):
    with pytest.raises(ValueError, match="between 1 and 10"):
        DeviceModel().run(depth)


def test_invalid_device_verdict_aborts_instead_of_reporting_coverage():
    device = DeviceModel()
    original = device.call

    def forged(method, params):
        result = original(method, params)
        if method == "lookup":
            result["valid"] = False
        return result

    device.call = forged
    with pytest.raises(AssertionError, match="lookup disagrees"):
        device.run(1)
    assert not any(
        event.get("event") == "extra_long.complete" for event in device.events
    )
