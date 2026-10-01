package com.satoshilabs.trezor.ward.relay;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.time.Duration;
import java.util.HexFormat;
import java.util.List;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * The Java binding of the <b>wardd relay</b> -- for Lark and any other JVM host that talks to a
 * Trezor.
 *
 * <p>{@code wardd} is the local WARD service: it holds the wallet's replica (in Evolu), the WM
 * client and the order of every sync, catch-up and flush. A binding carries messages between it
 * and the device on the session the host already holds, and nothing more -- the same contract the
 * Connect, Python and Rust bindings implement ({@code packages/ward-core/relay.md} in
 * trezor-suite, version 1.x):
 *
 * <pre>
 * client -&gt; wardd   {id, method, params}
 * wardd  -&gt; client  {id, deviceCall: {name, message}}    send this to the device
 * client -&gt; wardd   {id, deviceReply: {name, message}}   what the device said, pulls included
 * wardd  -&gt; client  {id, result} | {id, error: {code, message}}
 * </pre>
 *
 * <p>Calls are sequential and blocking, as a device session's calls are. One instance is one
 * socket; not for concurrent use.
 */
public final class WarddClient implements AutoCloseable {
    public static final URI DEFAULT_URL = URI.create("ws://127.0.0.1:21329");
    public static final String RELAY_PROTOCOL_VERSION = "1.0";

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final HexFormat HEX = HexFormat.of();
    private static final Object CLOSED = new Object();

    private final WebSocket socket;
    private final BlockingQueue<Object> inbox;
    private final Duration timeout;
    private long nextId = 1;

    private WarddClient(WebSocket socket, BlockingQueue<Object> inbox, Duration timeout) {
        this.socket = socket;
        this.inbox = inbox;
        this.timeout = timeout;
    }

    public static WarddClient connect(URI url, String token) throws WarddException {
        return connect(url, token, Duration.ofMinutes(5));
    }

    /**
     * Open the socket and say hello with the pairing token. {@code timeout} bounds every wait for
     * wardd -- generous by default, since a conversation waits on the user confirming on the device.
     *
     * <p>NO Origin header is sent: only a browser sends one, and wardd checks it against its
     * allow-list; a local process is admitted on the token alone.
     */
    public static WarddClient connect(URI url, String token, Duration timeout) throws WarddException {
        BlockingQueue<Object> inbox = new LinkedBlockingQueue<>();
        WebSocket socket;
        try {
            socket = HttpClient.newHttpClient()
                    .newWebSocketBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .buildAsync(url, new Inbox(inbox))
                    .get(15, TimeUnit.SECONDS);
        } catch (ExecutionException | TimeoutException e) {
            throw new WarddException("unreachable", "wardd is not reachable at " + url, e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new WarddException("unreachable", "interrupted", e);
        }
        WarddClient client = new WarddClient(socket, inbox, timeout);
        ObjectNode hello = JSON.createObjectNode().put("version", RELAY_PROTOCOL_VERSION).put("token", token);
        try {
            client.call("hello", hello, null);
        } catch (WarddException e) {
            client.close();
            throw e;
        }
        return client;
    }

    /**
     * One call; a CONVERSATION when wardd needs the device, answered through {@code pipe}.
     *
     * <p>EVERY deviceCall GETS A deviceReply: a {@link PipeException} -- or a pipe that throws
     * anything at all -- goes back as a {@code Failure}, so wardd ends the conversation and
     * releases the wallet instead of waiting.
     */
    public JsonNode call(String method, ObjectNode params, WardPipe pipe) throws WarddException {
        long id = nextId++;
        ObjectNode frame = JSON.createObjectNode().put("id", id).put("method", method);
        frame.set("params", params == null ? JSON.createObjectNode() : params);
        send(frame);
        while (true) {
            JsonNode in = receive();
            if (in.path("id").asLong(-1) != id) {
                continue;
            }
            if (in.has("deviceCall")) {
                JsonNode call = in.get("deviceCall");
                DeviceMessage request = new DeviceMessage(
                        call.path("name").asText(),
                        call.path("message").isObject()
                                ? (ObjectNode) call.get("message")
                                : JSON.createObjectNode());
                ObjectNode reply = JSON.createObjectNode().put("id", id);
                reply.set("deviceReply", answer(pipe, request));
                send(reply);
                continue;
            }
            if (in.has("error")) {
                JsonNode error = in.get("error");
                throw new WarddException(error.path("code").asText("internal"), error.path("message").asText());
            }
            if (!in.has("result")) {
                throw new WarddException("protocol", "a frame with neither result nor error");
            }
            return in.get("result");
        }
    }

    /**
     * Select the wallet: by {@code wardId}, or the device's own (asked with {@code WardSync}) when
     * null. {@code evoluNode} is the 64-byte node the device returns for {@code EvoluGetNode};
     * wardd derives the replica's owner from its child {@code WARD}. A wardd started with
     * {@code --memory} needs none.
     */
    public JsonNode openStore(WardPipe pipe, byte[] wardId, byte[] evoluNode) throws WarddException {
        String id;
        if (wardId != null) {
            id = HEX.formatHex(wardId);
        } else {
            DeviceMessage ack;
            try {
                ack = pipe.call(new DeviceMessage("WardSync", JSON.createObjectNode()));
            } catch (PipeException e) {
                throw new WarddException("device_failure", "WardSync: " + e.getMessage(), e);
            }
            if (!"WardSyncAck".equals(ack.name()) || !ack.message().hasNonNull("ward_id")) {
                throw new WarddException("protocol", "the device reported no ward_id");
            }
            id = ack.message().get("ward_id").asText();
        }
        ObjectNode params = JSON.createObjectNode().put("wardId", id);
        if (evoluNode != null) {
            params.put("evoluNode", HEX.formatHex(evoluNode));
        }
        return call("openStore", params, null);
    }

    /**
     * Bring the device to the WM's head. {@code rejoin} recovers a device on a fork, discarding its
     * changes above it -- confirmed on the device; without it wardd answers {@code needs_rejoin}.
     */
    public JsonNode sync(WardPipe pipe, boolean rejoin) throws WarddException {
        return call("sync", JSON.createObjectNode().put("rejoin", rejoin), pipe);
    }

    /** Publish everything queued, syncing after each transition; batched up to {@code maxBatch}. */
    public JsonNode flush(WardPipe pipe, int maxBatch) throws WarddException {
        return call("flush", JSON.createObjectNode().put("maxBatch", maxBatch), pipe);
    }

    /** The replica's head and the WM's, for the store last opened. */
    public JsonNode status() throws WarddException {
        return call("status", null, null);
    }

    /**
     * Answer one pull from wardd's replica, for a host driving a pulling call itself. {@code staged}
     * is CUMULATIVE for a batched flush: every (entry_key, commit) folded so far.
     */
    public JsonNode serveEntry(ObjectNode request, List<byte[][]> staged) throws WarddException {
        ObjectNode params = JSON.createObjectNode();
        params.set("request", request);
        ArrayNode list = params.putArray("staged");
        for (byte[][] pair : staged) {
            list.addArray().add(HEX.formatHex(pair[0])).add(HEX.formatHex(pair[1]));
        }
        return call("serveEntry", params, null);
    }

    /** Store and publish what a write handed back (a WardLeafAck / WardFlushQueueAck body). */
    public JsonNode applyResult(ObjectNode result) throws WarddException {
        return call("applyResult", result, null);
    }

    @Override
    public void close() {
        try {
            socket.sendClose(WebSocket.NORMAL_CLOSURE, "").get(5, TimeUnit.SECONDS);
        } catch (Exception ignored) {
            // closing anyway
        }
        socket.abort();
    }

    private static ObjectNode answer(WardPipe pipe, DeviceMessage request) {
        ObjectNode reply = JSON.createObjectNode();
        try {
            if (pipe == null) {
                throw PipeException.broken("no device to answer " + request.name());
            }
            DeviceMessage response = pipe.call(request);
            reply.put("name", response.name());
            reply.set("message", response.message());
        } catch (PipeException e) {
            ObjectNode body = reply.put("name", "Failure").putObject("message");
            if (e.code() != null) {
                body.put("code", e.code());
            }
            body.put("message", String.valueOf(e.getMessage()));
        } catch (RuntimeException e) {
            reply.put("name", "Failure").putObject("message").put("message", String.valueOf(e));
        }
        return reply;
    }

    private void send(ObjectNode frame) throws WarddException {
        try {
            socket.sendText(JSON.writeValueAsString(frame), true).get(30, TimeUnit.SECONDS);
        } catch (Exception e) {
            throw new WarddException("closed", "could not send to wardd", e);
        }
    }

    private JsonNode receive() throws WarddException {
        Object item;
        try {
            item = inbox.poll(timeout.toMillis(), TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new WarddException("closed", "interrupted", e);
        }
        if (item == null) {
            throw new WarddException("timeout", "no answer from wardd within " + timeout);
        }
        if (item == CLOSED || item instanceof Throwable) {
            inbox.add(item); // stays closed for any later call
            throw new WarddException("closed", "wardd closed the connection");
        }
        try {
            return JSON.readTree((String) item);
        } catch (Exception e) {
            throw new WarddException("protocol", "wardd sent a frame that is not JSON", e);
        }
    }

    /** Collects whole text messages; pings are answered with pongs by the JDK itself. */
    private static final class Inbox implements WebSocket.Listener {
        private final BlockingQueue<Object> inbox;
        private final StringBuilder partial = new StringBuilder();

        Inbox(BlockingQueue<Object> inbox) {
            this.inbox = inbox;
        }

        @Override
        public CompletionStage<?> onText(WebSocket ws, CharSequence data, boolean last) {
            partial.append(data);
            if (last) {
                inbox.add(partial.toString());
                partial.setLength(0);
            }
            ws.request(1);
            return null;
        }

        @Override
        public CompletionStage<?> onClose(WebSocket ws, int status, String reason) {
            inbox.add(CLOSED);
            return null;
        }

        @Override
        public void onError(WebSocket ws, Throwable error) {
            inbox.add(error);
        }
    }
}
