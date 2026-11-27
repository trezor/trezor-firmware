# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""Exercise a missing writer's records with two independent wardd stores and one manager."""

import os
import socket
import subprocess
import time
from contextlib import ExitStack, contextmanager

import pytest

from trezorlib import ward, ward_relay

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_app import ward_app_pinned  # noqa: F401

pytestmark = [
    pytest.mark.ward,
    pytest.mark.models("core"),
    pytest.mark.ward_transport("connect"),
]


@contextmanager
def _service(suite, tmp_path, name, entry, *args):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    log = tmp_path / (name + ".log")
    with log.open("w") as output:
        proc = subprocess.Popen(
            [
                "node",
                "--import",
                "tsx",
                "packages/wardd/src/" + entry,
                "--memory",
                "--port",
                str(port),
                *args,
            ],
            cwd=suite,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and proc.poll() is None:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                pytest.fail(f"{name} did not start: {log.read_text()}")
            yield port
        finally:
            proc.terminate()
            proc.wait(timeout=10)


def test_unsynchronized_host_reverts_and_writes(session, tmp_path):
    suite = os.environ.get("WARDD_SUITE_DIR")
    if not suite:
        pytest.skip("set WARDD_SUITE_DIR to run with wardd and its development manager")
    token = tmp_path / "token"
    token.write_text("ward-recovery-test")
    with ExitStack() as stack:
        wm = stack.enter_context(_service(suite, tmp_path, "manager", "wmCli.ts"))
        hosts = []
        for name in ("writer", "recovering"):
            port = stack.enter_context(
                _service(
                    suite,
                    tmp_path,
                    name,
                    "cli.ts",
                    "--token-file",
                    str(token),
                    "--data-dir",
                    str(tmp_path / name),
                    "--wm",
                    f"http://127.0.0.1:{wm}",
                )
            )
            host = stack.enter_context(
                ward_relay.WarddClient(token.read_text(), f"ws://127.0.0.1:{port}")
            )
            ward_relay.open_store(session, host)
            assert ward_relay.sync(session, host)["counter"] == 0
            hosts.append(host)
        writer, recovering = hosts
        with session.test_ctx as ctx:
            ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
            ward.queue_set_entry(session, "TEST", b"address", b"first label")
        assert ward_relay.flush(session, writer)["counter"] == 1
        assert ward_relay.status(recovering)["behind"]
        targets = ward_relay.recovery_targets(recovering)
        assert [(t["counter"], t["root"]) for t in targets] == [(0, None)]
        with session.test_ctx as ctx:
            ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
            result = ward_relay.revert(session, recovering, 0, None)
        assert result["counter"] == result["synced"]["counter"] == 2
        assert result["root"] is None
        assert not ward_relay.status(recovering)["behind"]
        with session.test_ctx as ctx:
            ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
            ward.queue_set_entry(session, "TEST", b"other", b"new label")
        assert ward_relay.flush(session, recovering)["counter"] == 3
