"""One shared relay engine; the HWI owns all device I/O and protobuf encoding."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ._native import Client

DEFAULT_URL = "ws://127.0.0.1:21329"


class WardAdapter:
    def __init__(self, token: str | None = None, url: str = DEFAULT_URL) -> None:
        if token is None:
            token = (Path.home() / ".trezor-ward/token").read_text().strip()
        self._client = Client(url, token)

    def __enter__(self) -> WardAdapter:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def start(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return json.loads(self._client.start(method, json.dumps(params or {})))

    def resume(self, name: str, message: dict[str, Any]) -> dict[str, Any]:
        return json.loads(self._client.resume(name, json.dumps(message)))

    def answer_ward_request(self, name: str, message: dict[str, Any]) -> dict[str, Any]:
        """Return a named WARDProofAck for the HWI to send on its current channel."""
        return json.loads(self._client.answer_ward_request(name, json.dumps(message)))[
            "deviceCall"
        ]

    def call(
        self,
        method: str,
        params: dict[str, Any],
        device_call: Callable[[str, dict[str, Any]], tuple[str, dict[str, Any]]],
    ) -> dict[str, Any]:
        """Run relay steps through the caller's existing session callback."""
        step = self.start(method, params)
        try:
            while "deviceCall" in step:
                request = step["deviceCall"]
                try:
                    name, message = device_call(request["name"], request["message"])
                except Exception:
                    # End wardd's conversation so a disconnected HWI cannot hold its lock.
                    name, message = "Failure", {"message": "HWI device call failed"}
                step = self.resume(name, message)
            if "error" in step:
                error = step["error"]
                raise RuntimeError(
                    f"{error.get('code', 'internal')}: {error.get('message', '')}"
                )
            return step["result"]
        except Exception:
            self.close()
            raise

    def set_logging(self, enabled: bool) -> None:
        self._client.set_logging(enabled)
