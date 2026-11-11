"""Isolate native transport failures before involving wardd or a WARD manager."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from trezorlib import messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.ward_service import ward_service_selector

from .test_ward_relay import SUITE_DIR

pytestmark = [
    pytest.mark.models("t3t1", "t3w1"),
    pytest.mark.skipif(not SUITE_DIR, reason="WARDD_SUITE_DIR is not set"),
]

# Use the production codec and transport, without the daemon, backend, or WebSocket.
# Emit phase names and sanitized adapter errors, never USB identifiers or payloads.
PROBE = r"""
import { once } from 'node:events';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { openServiceTransport, ServiceTimeout } = require('./src/serviceTransport.ts');
const { DeviceServiceConnection } = require('./src/deviceService.ts');

const [selector, mode] = process.argv.slice(1);
const phase = value => console.log(JSON.stringify({ phase: value }));
const watchdog = setTimeout(() => {
    phase('probe-deadline');
    process.exit(2);
}, 15000);
try {
    for (let cycle = 0; cycle < (mode === 'reopen' ? 3 : 1); cycle++) {
        phase('opening');
        const transport = await openServiceTransport(selector);
        const connection = new DeviceServiceConnection(transport, {
            call: async () => { throw new Error('Unexpected backend call'); },
            close: () => {},
        });
        let bound = false;
        try {
            await connection.announce();
            bound = true;
            phase('bound');
            if (mode !== 'reopen') {
                for (let poll = 0; poll < 10; poll++) {
                    try {
                        await transport.read(100);
                        throw new Error('Unexpected report while idle');
                    } catch (error) {
                        if (!(error instanceof ServiceTimeout)) throw error;
                    }
                }
                phase('idle-polls-passed');
                // Python now exercises the wallet while this USB handle stays open.
                const proceed = once(process.stdin, 'data');
                phase('wallet-ready');
                await proceed;
                await connection.announce();
                phase('binding-still-responsive');
            }
        } finally {
            try {
                if (bound) {
                    await connection.announce(true);
                    phase('unbound');
                }
            } finally {
                await transport.close();
                phase('released');
            }
        }
    }
    phase('complete');
} catch (error) {
    console.log(JSON.stringify({ phase: 'failed', error: error.message }));
    process.exitCode = 1;
} finally {
    clearTimeout(watchdog);
    process.stdin.pause();
}
"""


@pytest.mark.parametrize("mode", ["reopen", "idle-wallet"])
def test_native_service_transport(session: Session, tmp_path: Path, mode: str) -> None:
    assert SUITE_DIR is not None
    process = subprocess.Popen(
        [
            "node",
            "--import",
            "tsx",
            "--input-type=module",
            "-e",
            PROBE,
            ward_service_selector(session.client.transport),
            mode,
        ],
        cwd=Path(SUITE_DIR) / "packages" / "wardd",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = ""
    try:
        if mode == "idle-wallet":
            assert process.stdout is not None
            while line := process.stdout.readline():
                output += line
                if '"wallet-ready"' in line:
                    break
            assert '"wallet-ready"' in output, output
            reply = session.call(messages.Ping(message="ward-coexistence"))
            assert isinstance(reply, messages.Success)
            assert reply.message == "ward-coexistence"
        remainder, _ = process.communicate(input="continue\n", timeout=20)
        output += remainder
        assert process.returncode == 0, output
        phases = [json.loads(line)["phase"] for line in output.splitlines()]
        assert phases[-1] == "complete"
        assert phases.count("released") == (3 if mode == "reopen" else 1)
        if mode == "idle-wallet":
            assert "binding-still-responsive" in phases
    finally:
        if process.poll() is None:
            process.kill()
            remainder, _ = process.communicate(timeout=5)
            output += remainder
        (tmp_path / "native-transport.log").write_text(output)
        print(output)
