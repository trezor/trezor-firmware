package com.satoshilabs.trezor.ward.relay;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** The relay client against a scripted wardd, and -- with WARDD_SUITE_DIR -- against the real one. */
class WarddClientTest {
    private StubWardd wardd;

    @BeforeEach
    void start() throws Exception {
        wardd = new StubWardd();
        // sync: WardSync then WardReconcile (after a ping), both replies echoed back
        wardd.scripts.put("sync", (conn, frame) -> {
            long id = frame.get("id").asLong();
            conn.ping();
            conn.send(deviceCall(id, "WardSync"));
            JsonNode first = conn.recv().get("deviceReply");
            conn.send(deviceCall(id, "WardReconcile"));
            JsonNode second = conn.recv().get("deviceReply");
            ObjectNode result = StubWardd.JSON.createObjectNode().put("id", id);
            result.putObject("result").putArray("replies").add(first).add(second);
            conn.send(result);
        });
        wardd.scripts.put("refused", (conn, frame) ->
                conn.send(StubWardd.error(frame.get("id").asLong(), "needs_rejoin", "fork at 3")));
        wardd.scripts.put("echo", (conn, frame) -> {
            ObjectNode result = StubWardd.JSON.createObjectNode().put("id", frame.get("id").asLong());
            result.putObject("result").put("big", "x".repeat(70_000)).set("params", frame.get("params"));
            conn.send(result);
        });
    }

    @AfterEach
    void stop() throws Exception {
        wardd.close();
    }

    private static ObjectNode deviceCall(long id, String name) {
        ObjectNode f = StubWardd.JSON.createObjectNode().put("id", id);
        f.putObject("deviceCall").put("name", name).putObject("message");
        return f;
    }

    @Test
    void helloCarriesTheTokenAndNoOrigin() throws Exception {
        WarddClient.connect(wardd.url(), "good").close();
        JsonNode hello = wardd.received.get(0);
        assertEquals("hello", hello.get("method").asText());
        assertEquals("1.0", hello.at("/params/version").asText());
        assertEquals("good", hello.at("/params/token").asText());
        assertNull(wardd.origins.get(0), "only a browser sends Origin");
    }

    @Test
    void aWrongTokenIsRefusedWithItsCode() {
        WarddException e = assertThrows(WarddException.class, () -> WarddClient.connect(wardd.url(), "bad"));
        assertEquals("unauthorised", e.code());
    }

    @Test
    void warddNotRunningIsSaidPlainly() {
        WarddException e = assertThrows(
                WarddException.class, () -> WarddClient.connect(URI.create("ws://127.0.0.1:1"), "good"));
        assertEquals("unreachable", e.code());
    }

    @Test
    void aConversationAnswersEachDeviceCallInOrder() throws Exception {
        List<String> seen = new ArrayList<>();
        try (WarddClient client = WarddClient.connect(wardd.url(), "good")) {
            JsonNode out = client.sync(request -> {
                seen.add(request.name());
                return new DeviceMessage(request.name() + "Ack", StubWardd.JSON.createObjectNode().put("n", seen.size()));
            }, false);
            assertEquals(List.of("WardSync", "WardReconcile"), seen);
            assertEquals("WardSyncAck", out.at("/replies/0/name").asText());
            assertEquals(2, out.at("/replies/1/message/n").asInt());
        }
    }

    @Test
    void deviceFailuresAndBrokenPipesBothGoBackAsFailures() throws Exception {
        try (WarddClient client = WarddClient.connect(wardd.url(), "good")) {
            JsonNode out = client.sync(r -> {
                throw PipeException.failure("Failure_DataError", "no");
            }, false);
            assertEquals("Failure", out.at("/replies/0/name").asText());
            assertEquals("Failure_DataError", out.at("/replies/0/message/code").asText());
            out = client.sync(r -> {
                throw new IllegalStateException("gone");
            }, false);
            assertTrue(out.at("/replies/1/message/message").asText().contains("gone"));
        }
    }

    @Test
    void largeFramesAndErrorCodes() throws Exception {
        try (WarddClient client = WarddClient.connect(wardd.url(), "good")) {
            JsonNode out = client.call("echo", StubWardd.JSON.createObjectNode().put("blob", "y".repeat(300)), null);
            assertEquals(70_000, out.get("big").asText().length());
            assertEquals("y".repeat(300), out.at("/params/blob").asText());
            WarddException e = assertThrows(WarddException.class, () -> client.call("refused", null, null));
            assertEquals("needs_rejoin", e.code());
        }
    }

    @Test
    void againstRealWardd() throws Exception {
        String suite = System.getenv("WARDD_SUITE_DIR");
        if (suite == null) {
            return;
        }
        Path dir = Files.createTempDirectory("ward-relay-java");
        Files.writeString(dir.resolve("token"), "java-test");
        int port;
        try (java.net.ServerSocket probe = new java.net.ServerSocket(0)) {
            port = probe.getLocalPort();
        }
        // `node --import tsx`, not the tsx binary, which would leave a child node behind when killed
        Process proc = new ProcessBuilder("node", "--import", "tsx", "packages/wardd/src/cli.ts", "--memory",
                        "--port", String.valueOf(port), "--data-dir", dir.toString(),
                        "--token-file", dir.resolve("token").toString())
                .directory(Path.of(suite).toFile())
                .redirectErrorStream(true)
                .redirectOutput(dir.resolve("wardd.log").toFile())
                .start();
        try {
            URI url = URI.create("ws://127.0.0.1:" + port);
            WarddClient client = null;
            for (int i = 0; i < 100 && client == null; i++) {
                try {
                    client = WarddClient.connect(url, "java-test", Duration.ofSeconds(10));
                } catch (WarddException e) {
                    Thread.sleep(100);
                }
            }
            assertTrue(client != null, "wardd started");
            try (WarddClient c = client) {
                JsonNode opened = c.openStore(null, new byte[32], null);
                assertEquals(0, opened.get("counter").asInt());
                assertTrue(c.status().get("wmCounter").isNull());
            }
            WarddException e = assertThrows(WarddException.class, () -> WarddClient.connect(url, "wrong"));
            assertEquals("unauthorised", e.code());
        } finally {
            proc.destroy();
            proc.waitFor();
        }
    }
}
