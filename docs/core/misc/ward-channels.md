# WARD: who talks to whom

WARD splits its two conversations across two channels, and which conversation goes where is the whole
of this document.

```
  DisplayApp  (user-facing; a PoC for what a wallet will do itself)
     │
     │  WardGetEntry / WardSetEntry / WardFlushQueue / WardQueue*
     │  ── over the WALLET CHANNEL, the ordinary interface ──
     ▼
  Trezor
     │
     │  WardSyncRequest / WardServiceFetch / WardPublish
     │  ── over the SERVICE CHANNEL, an interface of the device's own ──
     ▼
  WARD host app + wardd   (owns the replica, speaks to the backend)
     │
     ▼
  WARD backend / WM
```

**The user-facing app** — DisplayApp today — reaches the device over the **wallet channel**, the
ordinary interface any host uses. It asks the device to show, write or publish an entry, and that is
the whole of its part: it never sees a value it did not supply, it holds no key, and on a service
build it is handed no leaf. It is a proof of concept for functionality a wallet will eventually carry
itself, which is why it belongs on the wallet channel rather than beside it.

**The device** is the only party that holds keys. It derives the keyed path, seals the parts, derives
the root, and decides what reaches the screen.

**The WARD host app together with wardd** owns the replica and speaks to the backend and the WM.
Both sit behind the **service channel**, and after the service announces itself the device is the sole
initiator on it — see `messages-ward-service.proto` for why that inversion is forced rather than
chosen.

**What the service channel decouples is the BACKEND, not the user-facing app.** WARD's replica
traffic — the sync, the fetch and the publish — leaves the device on its own interface and never
crosses the wallet channel. So a wallet with no interest in WARD is unaffected: it is never asked to
serve a leaf, never asked to hold a root, never asked to proxy anything, and needs no knowledge that
WARD exists. Suite, Sparrow or anything else can share the ordinary interface with a WARD-capable app
and see none of this.

That is the whole of the claim, and it is worth stating what it is *not*: WARD's user-facing
operations do not avoid the wallet channel — they arrive on it, by design, because the app that sends
them is standing in for a wallet. What avoids it is everything behind them.

## What differs between the two builds

WARD's transport is chosen at **build time** and a firmware serves it one way only.

| | connect build | service build (`--ward-service-channel`) |
|---|---|---|
| who owns the replica | the calling app, on the wallet channel | the WARD host app + wardd, behind the service channel |
| how the device reads a leaf | `WardEntryRequest` on the wallet channel, answered by the caller inside the workflow it interrupted | `WardServiceFetch` on the service channel |
| how a write lands | the device returns `WardLeafAck`; the caller must store it | the device publishes itself and returns `WardMutationApplied`, which carries no leaf |
| who syncs | the caller drives the sync round | the device drives its own sync when an operation needs one |

The difference is where the replica lives, and therefore how much a caller on the wallet channel has
to be. On a connect build it has to own the replica as well as invoke the operations; on a service
build it invokes and nothing more.

Which of the two a firmware is cannot be asked over the wire, deliberately: a host that could be
*told* could be lied to about it. Hosts that need to care are told by their operator (connect-cli's
`--service` flag is exactly such an assertion, and it fails closed when it is wrong).

### And what differs between the two transports

A service build carries the dedicated interface whatever protocol the model speaks, and **the
interface speaks the V1 codec on every model, including THP ones.** The interface is a USB
descriptor and knows nothing about which protocol runs on the wallet interface, so the two are
independent — a T3W1 has a THP wallet channel and a codec service endpoint.

That is a deliberate choice rather than a limitation. WARD's own cryptography is what makes a WARD
state trustworthy — leaf sealing under device-derived keys, the MPT proof against the device-trusted
root, the WM attestation, a counter and mac the device computed itself — so a transport that
authenticates the daemon buys no property the protocol does not already have. What a THP service
channel does buy is cost: a private dispatcher, channel reattachment, replacement semantics, a
persistent daemon pin whose first bind can be denied by anyone who reaches the interface first, and
a channel table shared with the wallet interface and evicted by a global LRU. None of that is built
by default.

The THP service path is kept compiling behind `--ward-service-thp`, which requires
`--ward-service-channel`. It is not built for any shipping configuration; the column below
describes it so the choice stays reviewable.

| | THP service channel (`--ward-service-thp`) | codec service endpoint (default) |
|---|---|---|
| what binding records | interface, channel id and session id | the interface, and nothing else |
| daemon identity | the Noise static key, pinned in flash | **none** — see below |
| what inverts the direction | the dispatcher lets go (`release_dispatch`), leaving the workflow the only reader | the reader keeps the interface and routes the answer into the workflow's mailbox |
| a daemon restart | a new channel; the old binding counts only while its channel is open | just another announcement, answered again |
| resetting the binding | `WardResetService`, a held confirmation | nothing to reset |
| the large message buffer | shared with the wallet channel, leased per message | the same, leased for the length of one RPC |
| the size a message may claim | THP's own framing bounds it | bounded explicitly: 512 B unbound or idle, `PROTOBUF_BUFFER_SIZE` during an RPC, above which it is drained and refused without allocating |
| which THP channel tables it uses | the shared ones, `MAX_INTERFACES` counts it | none: the interface is never handed to `ThpContext` |

**The codec endpoint authenticates nobody, and that is the design.** A codec transport carries no
handshake, so `WardServiceOpen` establishes only that a process is listening on the interface the
operating system gave to `wardd`. The interface is the authorisation boundary — a separate OS claim
from the wallet interface — and it is the whole of the transport-level check.

Nothing rests on it. A hostile process that can open the interface can fail an operation, answer
wrongly, or force an unnecessary synchronisation; it cannot inject state. What accepts an answer is
leaf authenticity under device-derived keys, the MPT proof against the device-trusted root, the WM
attestation, and a counter and mac the device computed itself — and none of those ask who sent the
bytes.

The same question arises one layer up, about the WARD *app* rather than the daemon, and is answered
the same way — see "Which party a request came from" below.

## Which party a request came from

**The daemon is pinned only on a `--ward-service-thp` build, which nothing ships.** By default the
service endpoint pins nobody, exactly as the codec column above says, and the paragraph below
describes the gated path. The first daemon to announce itself on the WARD interface
has its static public key written to flash (`storage.ward.get_service_host_key`), and every other key is refused
from then on. Pairing alone would not do: it proves a host holds a credential this device issued, and
every paired host holds one, so "some paired host" is the wrong granularity for the party the device
asks for proofs. Recovering from a lost daemon key is an ownership migration with a user decision in
it — `WardResetService` — and it discards no data.

**The WARD-capable host is pinned too, and there is exactly one of it — on THP.** The first host to
send a user-facing WARD message on the wallet channel has its static public key written to flash
(`storage.ward.get_app_host_key`) after the user holds to allow it, and every other key is refused
from then on. `WardResetApp` retires that pin, on a held confirmation, and discards no data.

**On protocol v1 there is no pin, because there is no identity.** A codec transport carries no
handshake, so the device cannot tell one connected application from another by any means — not
weakly, not at all. Failing closed there would leave WARD unavailable on every model without THP,
including Safe 5, so the pin is replaced by what v1 has always used instead of identity: the user,
per operation, on the device's own screen.

WHAT WAS MISSING WAS ORDERING, not confirmations. Every user-facing WARD operation already confirms,
and a read *displays* its value and returns only `Success` so the plaintext never reaches the host.
But those screens carry the value among their properties, so the secret is on the display by the
time the user is asked — an acknowledgement, not a decision. That is sound while a pin has already
decided who may trigger it. With no pin, **triggering a read is the disclosure.**

So on v1 the six operations that can put a stored value on screen — `WardGetEntry`,
`WardQueueGetEntry`, `WardQueueSetEntry`, `WardQueueDeleteEntry`, `WardPinCachedEntry`,
`WardEraseCachedEntry` — are preceded by a screen showing the domain and key alone, answered while
the value is still unrevealed. It is asked in the wire filter, before the handler has looked at the
request, which is the only place it can run and still be ahead of the disclosure; a consequence is
that it is asked even when the operation turns out to be a no-op. The operations that show back only
what the caller sent, and the replica plumbing that shows nothing, are not asked about.

What this does not do is make `app_id` a permission. Any connected application may still *ask* to
display any entry — it simply cannot do so without the user reading which one first. See the gap in
`common.require_key`, which is the deeper problem the THP pin also only papers over.

Note carefully what this is and is not. It is **not** a boundary between "the wallet" and "the WARD
app" — they share the ordinary interface, and in production they are expected to be the same program.
It is a bound on how many parties may operate WARD on one device: one, chosen by the user, rather
than every host that has ever paired. Several hosts can be connected at once on that interface, and
without the pin any of them could read, write or queue this wallet's entries.

**`app_id` remains a namespace rather than a permission.** It arrives on the wire, so the pinned host
may name any `app_id` and reach any app's entries; the pin narrows who can do that to one host but
does not stop it. The intended model has the device fill `app_id` in from the caller's identity, which
the pin now makes possible — it changes `entry_key` derivation, so it is a breaking change of its own.
The gap is recorded at `apps.ward.common.require_key`, and closing it is the work the pin starts.

Both checks are enforced where they cannot be forgotten: the daemon's in the `WardServiceOpen`
handler, which is the only way to bind that role, and the app's in a `trezor.wire` filter installed at
boot (`apps.ward.app_role.ward_app_filter`), so a WARD handler added later is covered without anyone
remembering to cover it.

## The debug harness

`connect-cli`'s `ward_*` commands and `packages/connect-cli/e2e/ward-queue.sh` in trezor-suite stand
in for the user-facing app, and `packages/connect-cli/e2e/ward-service-daemon.py` stands in for the
WARD host app and wardd together. They exist so both conversations can be exercised end to end from a
shell against real firmware.

They are a harness and not an example: the CLI reaches the device over the wallet channel, which is
where the user-facing operations belong anyway, but a real app would not do it with `--pairing=skip`.
Skipped pairing issues no credential, and connect then generates a fresh static key per run — so the
harness has to pair once for real and reuse the persisted credential, or the pin above would see a
different app on every invocation. That requirement is a feature of the harness meeting the same rule
as everything else, not an exception carved out for it.
