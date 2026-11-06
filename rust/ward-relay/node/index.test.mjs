import assert from "node:assert/strict";
import { once } from "node:events";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { setTimeout as delay } from "node:timers/promises";
import { test } from "node:test";

import { WardAdapter, WardError } from "./index.js";

const { WebSocketServer } = createRequire(import.meta.url)("ws");

async function server(t, handle) {
  const wss = new WebSocketServer({ port: 0, host: "127.0.0.1" });
  await once(wss, "listening");
  t.after(() => {
    for (const socket of wss.clients) socket.terminate();
    wss.close();
  });
  wss.on("connection", (socket) => {
    socket.on("message", async (data) => {
      const frame = JSON.parse(data);
      if (frame.method === "hello") {
        assert.equal(frame.params.token, "test-token");
        socket.send(
          JSON.stringify({ id: frame.id, result: { version: "1.0" } }),
        );
      } else {
        await handle(frame, (message) =>
          socket.send(JSON.stringify({ id: frame.id, ...message })),
        );
      }
    });
  });
  return WardAdapter.connect({
    url: `ws://127.0.0.1:${wss.address().port}`,
    token: "test-token",
  });
}

test("forwards device calls and nested proof pulls on the supplied HWI session", async (t) => {
  const adapter = await server(t, async (frame, send) => {
    if (frame.method === "sync")
      send({ deviceCall: { name: "WARDSync", message: {} } });
    else if (frame.method === "answerProofRequest") {
      assert.deepEqual(frame.params.request, { entry_key: "aa" });
      send({ result: { proof: [] } });
    } else {
      assert.deepEqual(frame.deviceReply, {
        name: "WARDSyncAck",
        message: { nonce: "ff" },
      });
      send({ result: { counter: 1 } });
    }
  });
  const result = await adapter.call("sync", {}, async (request) => {
    assert.equal(request.name, "WARDSync");
    const proof = await adapter.answerWardRequest("WARDProofRequest", {
      entry_key: "aa",
    });
    assert.deepEqual(proof, { name: "WARDProofAck", message: { proof: [] } });
    return { name: "WARDSyncAck", message: { nonce: "ff" } };
  });
  assert.deepEqual(result, { counter: 1 });
  await adapter.close();
  await adapter.close();
  await assert.rejects(adapter.start("status"), /closed/);
});

test("native waits keep the JavaScript event loop responsive", async (t) => {
  const adapter = await server(t, async (_frame, send) => {
    await delay(150);
    send({ result: { counter: 0 } });
  });
  let ticks = 0;
  const timer = setInterval(() => {
    ticks++;
  }, 10);
  try {
    assert.deepEqual(await adapter.call("status"), { counter: 0 });
    assert.ok(ticks >= 5, `only ${ticks} event loop ticks during native I/O`);
  } finally {
    clearInterval(timer);
    await adapter.close();
  }
});

test("rejects non-WARD device calls and surfaces remote failures", async (t) => {
  const hostile = await server(t, (_frame, send) => {
    send({ deviceCall: { name: "SignTx", message: {} } });
  });
  let calls = 0;
  await assert.rejects(
    hostile.call("sync", {}, async () => {
      calls++;
    }),
    /non-WARD/,
  );
  assert.equal(calls, 0);
  const refused = await server(t, (_frame, send) => {
    send({ error: { code: "no_store", message: "sync first" } });
  });
  await assert.rejects(
    refused.call("status"),
    (error) => error instanceof WardError && error.code === "no_store",
  );
});

test("rejects overlapping conversations and recovers by closing after device failure", async (t) => {
  const adapter = await server(t, (_frame, send) => {
    send({ deviceCall: { name: "WARDSync", message: {} } });
  });
  let entered;
  const ready = new Promise((resolve) => {
    entered = resolve;
  });
  let release;
  const device = new Promise((resolve) => {
    release = resolve;
  });
  const first = adapter.call("sync", {}, async () => {
    entered();
    await device;
    throw new Error("device disconnected");
  });
  await ready;
  await assert.rejects(
    adapter.call("sync", {}, async () => {}),
    /already active/,
  );
  release();
  await assert.rejects(first, /device disconnected/);
  await assert.rejects(adapter.start("status"), /closed/);
});

test(
  "Connect uses the real Rust addon for device handoffs and proof callbacks",
  {
    skip: !process.env.WARD_SUITE_DIR,
  },
  async (t) => {
    const suite = process.env.WARD_SUITE_DIR;
    const load = (path) => import(pathToFileURL(`${suite}/${path}`).href);
    const { RustWardRelay } = await load("packages/connect/src/ward.ts");
    const { callWard } = await load(
      "packages/connect-core/src/api/wardMethods/wardAdapter.ts",
    );
    const settings = await load(
      "packages/connect-core/src/data/settingsStore.ts",
    );
    const { parseConnectSettings } = await load(
      "packages/connect-common/src/data/connectSettings.ts",
    );
    const adapter = await server(t, (frame, send) => {
      if (frame.method === "sync")
        send({ deviceCall: { name: "WARDSync", message: {} } });
      else if (frame.method === "answerProofRequest")
        send({ result: { proof: [] } });
      else send({ result: { counter: 1 } });
    });
    let callback;
    let calls = 0;
    const cmd = {
      relayCall: async (name) => {
        calls++;
        assert.equal(name, "WARDSync");
        assert.deepEqual(await callback({ entry_key: "aa" }), { proof: [] });
        return { type: "WARDSyncAck", message: { nonce: "ff", absent: null } };
      },
      setWardProofCallback: (next) => {
        callback = next;
      },
    };
    settings.set(
      parseConnectSettings({
        wardd: new RustWardRelay({ connect: async () => adapter }),
      }),
    );
    try {
      assert.deepEqual(await callWard(cmd, "wardInit", "sync", {}), {
        counter: 1,
      });
      assert.equal(calls, 1);
      assert.equal(callback, undefined);
      await assert.rejects(adapter.start("status"), /closed/);
    } finally {
      settings.set(parseConnectSettings({}));
      await adapter.close();
    }
  },
);
