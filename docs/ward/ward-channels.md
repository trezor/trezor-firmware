# WARD: who talks to whom

> **The service channel is DEPRECATED and off by default.** It is built only on request; expect
> removal, and do not build new work on it. The connect
> transport — everything below marked "wallet channel" — is the one WARD is developed and tested
> against. The service path has no `WardRollback` or `WardRecoverCounter` at all and its sync is
> chain-only with no `reconcile` fallback, so a daemon with incomplete replica history strands the
> device; and the two transports' WM authorisation surfaces have drifted apart in opposite
> directions. The document is kept because the split it describes still holds, and because what the second channel was *for*
> matters if the capability is ever rebuilt.

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
     │  WardSyncRequest / WardChainRequest / WardServiceFetch / WardPublish
     │  ── over the SERVICE CHANNEL, an interface of the device's own ──
     ▼
  WARD host app + wardd   (owns the replica, speaks to the backend)
     │
     ▼
  WARD backend / WM
```

**The user-facing app** reaches the device over the **wallet channel**, the
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

The service keeps the WM attestation separate from the history. A device that is behind
pulls pages of up to 64 links, newest first, and adopts the attested head after proving descent
from its stored head. A sync first asks for the WM's session challenge
(`WardSyncRequest.challenge_only`), then sends the device's nonce and session proof. A device
already at the attested head needs only those two exchanges. A publication carries its own
freshness nonce and keeps the session opened at sync.

Protocol v3 lets the codec daemon renew its binding while idle. Firmware ignores a renewal
during an RPC, and the next renewal rebinds the endpoint after a timeout. Version 4 removed the
WM head nonce. The current version is 5, which added the session challenge and proof; the device
requires an exact match. The service channel does not roll a restored WM forward; that runs on
the wallet channel only (see [roll-forward](ward_roll_forward.md)).

## What differs between the two builds

WARD's transport is chosen at **build time** and a firmware serves it one way only. The connect
build is the default; a service build is an opt-in build option. Bitcoin-only
firmware registers no WARD handlers at all, so asking for the channel there is refused rather than
silently dropped.

| | connect build (default) | service build (opt-in) |
|---|---|---|
| who owns the replica | the calling app, on the wallet channel | the WARD host app + wardd, behind the service channel |
| how the device reads a leaf | `WardEntryRequest` on the wallet channel, answered by the caller inside the workflow it interrupted | `WardServiceFetch` on the service channel |
| how a write lands | the device returns `WardLeafAck`; the caller must store it | the device publishes itself and returns `WardMutationApplied`, which carries no leaf |
| who syncs | the caller drives the sync round | the device drives its own sync when an operation needs one |

The difference is where the replica lives, and therefore how much a caller on the wallet channel has
to be. On a connect build it has to own the replica as well as invoke the operations; on a service
build it invokes and nothing more.

Which of the two a firmware is cannot be asked over the wire, deliberately: a host that could be
*told* could be lied to about it. Hosts that need to care are told by their operator, and such a
setting fails closed when it is wrong.

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
even when the service channel is.

A THP service path is kept behind a further build option, which requires the service build: there
is otherwise no interface for it to speak on. The column below describes it so the choice stays
reviewable.

| | THP service channel (gated) | codec service endpoint (default transport of a service build) |
|---|---|---|
| what binding records | interface, channel id and session id | the interface, and nothing else |
| daemon identity | the Noise static key, pinned in flash | **none** — see below |
| what inverts the direction | the dispatcher lets go, leaving the workflow the only reader | the reader keeps the interface and routes the answer into the workflow's mailbox |
| a daemon restart | a new channel; the old binding counts only while its channel is open | just another announcement, answered again |
| resetting the binding | `WardResetService`, a held confirmation | nothing to reset |
| the large message buffer | shared with the wallet channel, leased per message | the same, leased for the length of one RPC |
| the size a message may claim | THP's own framing bounds it | bounded explicitly: 512 B unbound or idle, `PROTOBUF_BUFFER_SIZE` during an RPC, above which it is drained and refused without allocating |
| which THP channel tables it uses | the shared ones, `MAX_INTERFACES` counts it | none: the interface is never handed to `ThpContext` |
| what bounds a half-read message | nothing directly — reassembly state sits in Rust until the peer is preempted for having gone quiet, or the channel is retransmitted to death | 500 ms between continuation reports, and the read is abandoned at its next report once the operation that wanted it has given up |

**A header is a promise of more, and the service endpoint holds its peer to it.** Every other
refusal in the codec is deferred until the message has been drained, so the wire is left at a frame
boundary and the next read starts on a real header. That is right for a message that arrives and is
exactly what would strand the reader on one that does not, so a message already in progress is
abandoned when either the gap between its reports exceeds 500 ms or the conversation it belongs to
is given up on — whichever comes first. The two are not redundant: the timeout bounds a peer that
goes quiet, and a peer that instead trickles reports just inside it is bounded by the second.

What that protects is not the framing, which cannot be resynchronised in a protocol with no sync
marks, but the RECEIVE BUFFER: the lease is taken when the header is parsed, so a frame that never
ends holds it forever, and on a THP build that buffer is the wallet's too. A stray continuation
report arriving after the frame was abandoned fails the magic check and is refused on its own.

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

**The daemon is pinned only on a THP service build.** By default the
service endpoint pins nobody, exactly as the codec column above says, and the paragraph below
describes the gated path. The first daemon to announce itself on the WARD interface
has its static public key written to flash, and every other key is refused
from then on. Pairing alone would not do: it proves a host holds a credential this device issued, and
every paired host holds one, so "some paired host" is the wrong granularity for the party the device
asks for proofs. Recovering from a lost daemon key is an ownership migration with a user decision in
it — `WardResetService` — and it discards no data.

**The WARD-capable host is pinned too, and there is exactly one of it — on THP.** The first host to
send a user-facing WARD message on the wallet channel has its static public key written to flash
after the user holds to allow it, and every other key is refused
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
display any entry — it simply cannot do so without the user reading which one first. That is the
deeper problem the THP pin also only papers over; see the [security gaps](gaps.md).

Note carefully what this is and is not. It is **not** a boundary between "the wallet" and "the WARD
app" — they share the ordinary interface, and in production they are expected to be the same program.
It is a bound on how many parties may operate WARD on one device: one, chosen by the user, rather
than every host that has ever paired. Several hosts can be connected at once on that interface, and
without the pin any of them could read, write or queue this wallet's entries.

**`app_id` remains a namespace rather than a permission.** It arrives on the wire, so the pinned host
may name any `app_id` and reach any app's entries; the pin narrows who can do that to one host but
does not stop it. The intended model has the device fill `app_id` in from the caller's identity, which
the pin now makes possible — it changes `entry_key` derivation, so it is a breaking change of its own.
Closing that gap is the work the pin starts.

Both checks are enforced where they cannot be forgotten: the daemon's in the `WardServiceOpen`
handler, which is the only way to bind that role, and the app's in a filter on every incoming
message, installed at boot, so a WARD handler added later is covered without anyone remembering to
cover it.
