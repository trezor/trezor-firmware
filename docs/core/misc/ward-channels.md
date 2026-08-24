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

## Which party a request came from

**The daemon is pinned.** The first daemon to announce itself on the WARD interface has its static
public key written to flash (`storage.ward.get_service_host_key`), and every other key is refused
from then on. Pairing alone would not do: it proves a host holds a credential this device issued, and
every paired host holds one, so "some paired host" is the wrong granularity for the party the device
asks for proofs. Recovering from a lost daemon key is an ownership migration with a user decision in
it — `WardResetService` — and it discards no data.

**The WARD-capable host is pinned too, and there is exactly one of it.** The first host to send a
user-facing WARD message on the wallet channel has its static public key written to flash
(`storage.ward.get_app_host_key`) after the user holds to allow it, and every other key is refused
from then on. `WardResetApp` retires that pin, on a held confirmation, and discards no data.

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
