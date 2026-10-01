# ward-relay (Java)

The Java binding of the **wardd relay**: it carries a WARD conversation between `wardd`, the local
WARD service, and a Trezor on the session a JVM host (Lark) already holds. wardd holds all of the
WARD logic; this library holds none. It implements the same contract as the Connect, Python
(`trezorlib.ward_relay`) and Rust (`rust/ward-relay`) bindings: `packages/ward-core/relay.md` in
trezor-suite, version 1.x.

## Using it

1. **Implement `WardPipe` on your Trezor session.** It receives a named message whose body is JSON
   (`DeviceMessage`) and returns the device's answer.
   - Map `name` to your message type, and use `ProtobufJson` for the body: bytes as hex, enums by
     name, absent fields omitted.
   - Handle button requests, PIN and passphrase as usual.
   - Return WARD pulls (`WardEntryRequest`, `WardChainRequest`) unanswered.
   - Throw `PipeException.failure(code, message)` when the device answers `Failure`.
2. **Connect:** `WarddClient.connect(url, token)`, then `openStore(pipe, wardId, evoluNode)`.
3. **Run the operation:** `sync(pipe, rejoin)`, `flush(pipe, maxBatch)` or `status()`. Each one is a
   single conversation on a single session.

## Scope

- **Desktop JVM, Java 17+:** it uses `java.net.http.WebSocket` and Jackson.
- **`ProtobufJson`** needs full protobuf-java with descriptors. protobuf-javalite on Android has
  none, and Android has no local Node to run wardd anyway. That platform needs its own decision.

## Building

```text
./build.sh                                  # a bare JDK: fetches the jars, compiles, runs JUnit
WARDD_SUITE_DIR=/path/to/trezor-suite ./build.sh   # also against the real wardd
mvn test                                    # the same, with Maven
```

`build.sh` checks the Java 17 API with `--release 17` when the JDK ships `ct.sym`. Without it, the
script checks only the language level; `mvn` always checks both.
