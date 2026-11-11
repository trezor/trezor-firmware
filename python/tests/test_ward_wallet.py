"""Wallet-only commands while wardd owns the independent backend interface."""

from __future__ import annotations

import pytest

from trezorlib.ward_relay import WarddError
from trezorlib.ward_wallet import Body, WardWalletClient

WARD_ID = "ab" * 32


def test_unbound_service_fails_without_requesting_backend_data() -> None:
    requested = []

    def device(name: str, body: Body) -> tuple[str, Body]:
        requested.append(name)
        return "WARDSyncAck", {"ward_id": WARD_ID, "service_bound": False}

    with pytest.raises(WarddError, match="No WARD service is bound"):
        WardWalletClient().call("sync", {}, device)
    assert requested == ["WARDSync"]


@pytest.mark.parametrize("applied", [False, True])
def test_updates_require_service_finalization(applied: bool) -> None:
    requested = []

    def device(name: str, body: Body) -> tuple[str, Body]:
        requested.append((name, body))
        replies = {
            "WARDSync": ("WARDSyncAck", {"ward_id": WARD_ID, "service_bound": True}),
            "WARDServiceSync": (
                "WARDServiceSyncAck",
                {"used_service": True, "ward_id": WARD_ID, "counter": 0},
            ),
            "WARDListPendingEdits": ("WARDListPendingEditsAck", {"pending_ids": []}),
            "WARDQueueUpdate": ("WARDQueueUpdateAck", {"pending_id": 7}),
            "WARDPerformBatch": (
                "WARDPerformBatchAck",
                {
                    "ward_id": WARD_ID,
                    "counter": 1,
                    "new_root": "cd" * 32,
                    "service_applied": applied,
                },
            ),
        }
        return replies[name]

    client = WardWalletClient()

    def update() -> Body:
        return client.call(
            "update",
            {
                "appId": "bitcoin",
                "address": "test-address",
                "networkSymbol": "btc",
                "metadata": {"label": "service"},
            },
            device,
        )

    if applied:
        assert update()["counter"] == 1
    else:
        with pytest.raises(WarddError, match="did not confirm"):
            update()
    queued = next(body for name, body in requested if name == "WARDQueueUpdate")
    assert bytes.fromhex(queued["new_value"]) == b'btc:{"label":"service"}'
    assert all(
        name not in ("WARDIngestAttestation", "WARDConfirmBatchByWM")
        for name, _ in requested
    )
