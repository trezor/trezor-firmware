"""Bounded WARD state/operation coverage, using a caller's real device bridge.

Two keys each hold no entry, an empty value, or a label. Equivalent logical
states at the same depth share their suffix exploration; ciphertexts, counters
and random nonces are not treated as distinct model states. The runner checks
the actual monotonic counter and device proofs after every operation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

MAX_DEPTH = 10
State = tuple[int | None, int | None]
Body = dict[str, Any]


@dataclass(frozen=True)
class Operation:
    method: str
    key: int = 0
    value: int | None = None

    @property
    def name(self) -> str:
        if self.method == "sync":
            return "sync"
        suffix = ""
        if self.method == "write":
            suffix = ".empty" if self.value == 0 else ".label"
        return f"{self.method}.{self.key}{suffix}"

    def next_state(self, state: State) -> State:
        values = list(state)
        if self.method == "write":
            values[self.key] = self.value
        elif self.method == "delete":
            values[self.key] = None
        return values[0], values[1]


OPERATIONS = (
    Operation("sync"),
    *(Operation("lookup", key) for key in range(2)),
    *(Operation("write", key, value) for key in range(2) for value in (0, 1)),
    *(Operation("delete", key) for key in range(2)),
)


def expected_coverage(max_depth: int) -> set[tuple[int, State, str]]:
    """Enumerate all reachable logical state/operation edges at each depth."""
    if not 1 <= max_depth <= MAX_DEPTH:
        raise ValueError(f"maximum depth must be between 1 and {MAX_DEPTH}")
    frontier: set[State] = {(None, None)}
    coverage = set()
    for depth in range(1, max_depth + 1):
        following = set()
        for state in frontier:
            for operation in OPERATIONS:
                coverage.add((depth, state, operation.name))
                following.add(operation.next_state(state))
        frontier = following
    return coverage


def run_extra_long(
    call: Callable[[str, Body], Body],
    confirm: Callable[[Callable[[], Body]], Body],
    display: Callable[[Body, str], None],
    log: Callable[[Body], None],
    address_prefix: str,
    max_depth: int = MAX_DEPTH,
    verify_lookup: Callable[[Body], Body] | None = None,
) -> Body:
    """Cover the finite model through depth 10; fail on the first discrepancy.

    Restoration uses ordinary authenticated writes, never root injection or WM
    resets. Its operations are logged separately from coverage edges.
    """
    expected = expected_coverage(max_depth)
    head = call("sync", {})
    if head["counter"] != 0 or head["root"] != "":
        raise AssertionError("--extra_long requires a fresh WARD wallet/manager")
    counter = 0
    state: State = (None, None)
    seen: set[tuple[int, State]] = set()
    covered: set[tuple[int, State, str]] = set()
    operations = 0
    deepest = 0

    def params(key: int) -> Body:
        return {
            "appId": "bitcoin",
            "address": f"{address_prefix}-extra-{key}",
            "networkSymbol": "btc",
        }

    def label(key: int) -> str:
        return f"WARD extra label {key}"

    def lookup(key: int, verification: bool = False) -> Body:
        result = (
            verify_lookup(params(key))
            if verification and verify_lookup
            else call("lookup", params(key))
        )
        if (
            result.get("valid") is not True
            or result.get("isMember") is not (state[key] is not None)
            or result.get("counter") != counter
            or result.get("wardId") != head["wardId"]
        ):
            raise AssertionError(f"lookup disagrees with model {state}: {result}")
        return result

    def apply(operation: Operation, depth: int, phase: str) -> None:
        nonlocal counter, state, operations, deepest
        before = state
        next_state = operation.next_state(state)
        advancing = operation.method == "write" or (
            operation.method == "delete" and state[operation.key] is not None
        )
        if operation.method == "sync":
            result = call("sync", {})
        elif operation.method == "lookup":
            result = lookup(operation.key)
        else:
            body = params(operation.key)
            if operation.method == "delete":
                body["delete"] = True
            elif operation.value == 0:
                body["valueHex"] = ""
            else:
                body["metadata"] = {"label": label(operation.key)}

            def invoke() -> Body:
                return call("update", body)

            result = confirm(invoke) if advancing else invoke()

        wanted_counter = counter + int(advancing)
        if (
            result.get("counter") != wanted_counter
            or result.get("wardId") != head["wardId"]
            or result.get("conflict")
            or result.get("localCacheError")
        ):
            raise AssertionError(f"{operation.name} returned an invalid head: {result}")
        if "root" in result:
            if bool(result["root"]) != any(value is not None for value in next_state):
                raise AssertionError(
                    f"{operation.name}: root emptiness disagrees with model"
                )
            if not advancing and result["root"] != head["root"]:
                raise AssertionError(f"{operation.name}: read/no-op changed the root")
            head.update(result)
        counter, state = wanted_counter, next_state
        if advancing:
            for key in range(2):
                lookup(key, verification=True)
            if operation.method == "write" and operation.value == 1:
                display(params(operation.key), label(operation.key))
        operations += 1
        deepest = max(deepest, depth)
        log(
            {
                "event": "extra_long.operation",
                "phase": phase,
                "depth": depth,
                "operation": operation.name,
                "before": before,
                "after": state,
                "counter": counter,
            }
        )

    def explore(depth: int) -> None:
        if depth == max_depth or (depth, state) in seen:
            return
        seen.add((depth, state))
        baseline = state
        for operation in OPERATIONS:
            apply(operation, depth + 1, "coverage")
            covered.add((depth + 1, baseline, operation.name))
            explore(depth + 1)
            # Return to the logical baseline, retaining the real counter history.
            for key, value in enumerate(baseline):
                if state[key] != value:
                    undo = (
                        Operation("delete", key)
                        if value is None
                        else Operation("write", key, value)
                    )
                    apply(undo, depth, "restore")

    explore(0)
    if covered != expected:
        raise AssertionError(f"incomplete coverage: missing {expected - covered}")
    for key in range(2):
        lookup(key)
    summary = {
        "event": "extra_long.complete",
        "maxDepth": deepest,
        "coveredEdges": len(covered),
        "expectedEdges": len(expected),
        "operationsIncludingRestore": operations,
        "counter": counter,
        "operationNames": [operation.name for operation in OPERATIONS],
        "model": "two keys; absent/empty/label; equivalent states merged per depth",
    }
    log(summary)
    return summary
