package com.satoshilabs.trezor.ward.relay;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.DataInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/** A scripted wardd: server-side RFC 6455 over a raw socket, one script per method. */
final class StubWardd implements AutoCloseable {
    interface Script {
        void run(Conn conn, JsonNode frame) throws IOException;
    }

    static final ObjectMapper JSON = new ObjectMapper();
    final List<JsonNode> received = new CopyOnWriteArrayList<>();
    final List<String> origins = new CopyOnWriteArrayList<>();
    final Map<String, Script> scripts = new ConcurrentHashMap<>();
    private final ServerSocket listener;

    StubWardd() throws IOException {
        listener = new ServerSocket(0, 50, InetAddress.getLoopbackAddress());
        Thread t = new Thread(this::serve);
        t.setDaemon(true);
        t.start();
    }

    URI url() {
        return URI.create("ws://127.0.0.1:" + listener.getLocalPort());
    }

    private void serve() {
        while (!listener.isClosed()) {
            try {
                Socket s = listener.accept();
                Thread t = new Thread(() -> handle(s));
                t.setDaemon(true);
                t.start();
            } catch (IOException e) {
                return;
            }
        }
    }

    private void handle(Socket s) {
        try (s) {
            Conn conn = new Conn(s);
            origins.add(conn.handshake());
            while (true) {
                JsonNode frame = conn.recv();
                received.add(frame);
                String method = frame.path("method").asText();
                long id = frame.path("id").asLong();
                if (method.equals("hello")) {
                    if (frame.path("params").path("token").asText().equals("good")) {
                        conn.send(JSON.createObjectNode().put("id", id).set("result", JSON.createObjectNode()));
                    } else {
                        conn.send(error(id, "unauthorised", "no"));
                    }
                    continue;
                }
                scripts.get(method).run(conn, frame);
            }
        } catch (Exception e) {
            // the client went away
        }
    }

    static ObjectNode error(long id, String code, String message) {
        ObjectNode f = JSON.createObjectNode().put("id", id);
        f.putObject("error").put("code", code).put("message", message);
        return f;
    }

    @Override
    public void close() throws IOException {
        listener.close();
    }

    static final class Conn {
        private final DataInputStream in;
        private final OutputStream out;

        Conn(Socket s) throws IOException {
            in = new DataInputStream(s.getInputStream());
            out = s.getOutputStream();
        }

        /** Answers the upgrade; returns the Origin header (null when none was sent). */
        String handshake() throws Exception {
            StringBuilder head = new StringBuilder();
            while (!head.toString().endsWith("\r\n\r\n")) {
                head.append((char) in.readUnsignedByte());
            }
            String key = null;
            String origin = null;
            for (String line : head.toString().split("\r\n")) {
                int colon = line.indexOf(':');
                if (colon < 0) {
                    continue;
                }
                String name = line.substring(0, colon).trim().toLowerCase();
                String value = line.substring(colon + 1).trim();
                if (name.equals("sec-websocket-key")) {
                    key = value;
                } else if (name.equals("origin")) {
                    origin = value;
                }
            }
            String accept = Base64.getEncoder().encodeToString(MessageDigest.getInstance("SHA-1")
                    .digest((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").getBytes(StandardCharsets.US_ASCII)));
            out.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                            + "Sec-WebSocket-Accept: " + accept + "\r\n\r\n")
                    .getBytes(StandardCharsets.US_ASCII));
            out.flush();
            return origin;
        }

        JsonNode recv() throws IOException {
            while (true) {
                int b0 = in.readUnsignedByte();
                int b1 = in.readUnsignedByte();
                if ((b1 & 0x80) == 0) {
                    throw new IOException("a client frame must be masked");
                }
                long n = b1 & 0x7f;
                if (n == 126) {
                    n = in.readUnsignedShort();
                } else if (n == 127) {
                    n = in.readLong();
                }
                byte[] mask = in.readNBytes(4);
                byte[] payload = in.readNBytes((int) n);
                for (int i = 0; i < payload.length; i++) {
                    payload[i] ^= mask[i % 4];
                }
                int opcode = b0 & 0x0f;
                if (opcode == 0x8) {
                    throw new IOException("closed");
                }
                if (opcode == 0x1) {
                    return JSON.readTree(payload);
                }
            }
        }

        void ping() throws IOException {
            out.write(new byte[] {(byte) 0x89, 2, 'h', 'i'});
            out.flush();
        }

        void send(JsonNode frame) throws IOException {
            byte[] data = JSON.writeValueAsBytes(frame);
            if (data.length < 126) {
                out.write(new byte[] {(byte) 0x81, (byte) data.length});
            } else if (data.length < 65536) {
                out.write(new byte[] {(byte) 0x81, 126, (byte) (data.length >> 8), (byte) data.length});
            } else {
                out.write(new byte[] {(byte) 0x81, 127});
                for (int i = 7; i >= 0; i--) {
                    out.write((int) ((long) data.length >> (8 * i)));
                }
            }
            out.write(data);
            out.flush();
        }
    }
}
