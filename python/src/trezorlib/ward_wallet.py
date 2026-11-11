"""Wallet operations for a device whose WARD backend uses the service interface.

This client opens no socket and supplies no proofs, signatures or replica data.
It sends wallet requests on the caller's existing session; the firmware handles
backend exchanges independently through wardd.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .ward_relay import WarddError

Body = dict[str, Any]
DeviceCall = Callable[[str, Body], tuple[str, Body]]


class WardWalletClient:
    def __init__(self) -> None:
        self.head: Body | None = None

    def __enter__(self) -> WardWalletClient:
        return self

    def __exit__(self, *exc: object) -> None:
        pass

    def answer_ward_request(self, name: str, body: Body) -> Body:
        raise WarddError(
            "device_failure", "WARD backend traffic reached the wallet channel"
        )

    def _ask(self, device: DeviceCall, name: str, body: Body, expected: str) -> Body:
        kind, reply = device(name, body)
        if kind != expected:
            raise WarddError(
                "device_failure", f"{name}: expected {expected}, received {kind}"
            )
        return reply

    def _installed(self, reply: Body, ward_id: str) -> Body:
        if reply.get("service_applied") is not True or reply.get("ward_id") != ward_id:
            raise WarddError(
                "device_failure", "WARD service did not confirm the publication"
            )
        self.head = {
            "wardId": ward_id,
            "counter": reply["counter"],
            "root": reply.get("new_root") or "",
        }
        return self.head

    def _sync(self, device: DeviceCall, params: Body) -> Body:
        initial = self._ask(device, "WARDSync", {}, "WARDSyncAck")
        ward_id = initial.get("ward_id")
        if not ward_id or (
            params.get("wardId") is not None and params["wardId"] != ward_id
        ):
            raise WarddError(
                "ward_id_mismatch",
                "WARD wallet identity differs from the requested wallet",
            )
        if initial.get("service_bound") is not True:
            raise WarddError(
                "device_failure",
                "No WARD service is bound; start wardd with --service-channel",
            )
        ack = self._ask(device, "WARDServiceSync", {}, "WARDServiceSyncAck")
        if ack.get("used_service") is not True or ack.get("ward_id") != ward_id:
            raise WarddError(
                "device_failure", "WARD service binding changed during sync"
            )
        self.head = {
            "wardId": ward_id,
            "counter": ack["counter"],
            "root": ack.get("root") or "",
        }
        pending = self._ask(
            device, "WARDListPendingEdits", {}, "WARDListPendingEditsAck"
        )
        for pending_id in pending.get("pending_ids", []):
            applied = self._ask(
                device,
                "WARDPerformBatch",
                {"pending_ids": [pending_id]},
                "WARDPerformBatchAck",
            )
            self._installed(applied, ward_id)
        return self.head

    def call(
        self, method: str, params: Body | None = None, device: DeviceCall | None = None
    ) -> Body:
        params = params or {}
        if method == "status":
            if self.head is None:
                raise WarddError("no_store", "sync first")
            return self.head
        if device is None:
            raise WarddError(
                "bad_request", "A wallet operation needs the device session"
            )
        if method == "sync":
            return self._sync(device, params)
        if method not in (
            "lookup",
            "update",
            "listEntries",
            "cacheEntry",
            "exportCache",
            "importCache",
            "validateCache",
        ):
            raise WarddError(
                "bad_request", f"Unsupported wallet service operation: {method}"
            )
        head = self._sync(device, params)
        ward_id = head["wardId"]
        if method in ("lookup", "update"):
            app = params.get("appId")
            address = params.get("address")
            network = params.get("networkSymbol")
            if not all(isinstance(value, str) for value in (app, address, network)):
                raise WarddError(
                    "bad_request", "appId, address and networkSymbol must be strings"
                )
            lookup = {
                "app_id": app,
                "address": address.encode().hex(),
                "key_type": "address",
                "proof": [],
            }
            removing = params.get("delete") is True
            if method == "lookup" or removing:
                ack = self._ask(device, "WARDLookup", lookup, "WARDLookupAck")
                if ack.get("ward_id") != ward_id:
                    raise WarddError("ward_id_mismatch", "Lookup names another wallet")
                if method == "lookup":
                    return {
                        "wardId": ward_id,
                        "valid": ack["valid"],
                        "isMember": ack["membership"],
                        "counter": ack["counter"],
                    }
                if ack.get("valid") is not True:
                    raise WarddError(
                        "device_failure", "Cannot delete without a valid proof"
                    )
                if ack.get("membership") is not True:
                    return head
            metadata = params.get("metadata", {})
            value = (
                ""
                if removing
                else (
                    network
                    + ":"
                    + json.dumps(
                        metadata,
                        separators=(",", ":"),
                        ensure_ascii=False,
                        allow_nan=False,
                    )
                )
                .encode()
                .hex()
            )
            value = params.get("valueHex", value)
            if (
                not isinstance(value, str)
                or len(value) % 2
                or any(c not in "0123456789abcdefABCDEF" for c in value)
            ):
                raise WarddError(
                    "bad_request", "valueHex must contain whole hexadecimal bytes"
                )
            queued = self._ask(
                device,
                "WARDQueueUpdate",
                {
                    "address": address.encode().hex(),
                    "new_value": value,
                    "app_id": app,
                    "delete": removing,
                },
                "WARDQueueUpdateAck",
            )
            ack = self._ask(
                device,
                "WARDPerformBatch",
                {"pending_ids": [queued["pending_id"]]},
                "WARDPerformBatchAck",
            )
            return self._installed(ack, ward_id)
        requests = {
            "listEntries": (
                "WARDListEntries",
                {
                    key: params[source]
                    for key, source in (
                        ("app_id", "appId"),
                        ("key_type", "keyType"),
                        ("device_id", "deviceId"),
                    )
                    if source in params
                },
            ),
            "cacheEntry": (
                "WARDCacheEntry",
                {
                    "entry_key": params.get("entryKey"),
                    "sticky": params.get("sticky") is True,
                },
            ),
            "exportCache": ("WARDCacheExport", {}),
            "importCache": ("WARDCacheImport", {"entries": params.get("entries", [])}),
            "validateCache": ("WARDValidateCache", {}),
        }
        name, body = requests[method]
        ack = self._ask(device, name, body, name + "Ack")
        return {"wardId": ward_id, **ack}
