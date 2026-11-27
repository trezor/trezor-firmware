# F9 Service channel

On the [wallet channel](../ward-channels.md#wallet-channel) the application relays every exchange
between the Trezor and wardd. On the
[dedicated service channel](../ward-channels.md#dedicated-service-channel) the application still
sends user-facing requests, but inside such a request the device itself asks wardd, on a separate
interface, for a leaf, a sync or a publication, and continues once it has verified the answer.

The channel changes transport and initiator, not trust. Everything wardd returns is verified as on
the wallet channel: leaves against the trusted root, heads against a WM attestation and wallet
history ([F6](f6-freshness.md)). Invariants:

- wardd can never start a workflow, interrupt signing, or create or activate a wallet session; all
  seed-derived work stays in the wallet workflow that started the operation.
- User-facing authority (entry operations, sync recovery, queue management, reset) stays on the
  wallet channel under the WARD application role.
- Every failure fails the operation closed and leaves the wallet channel undisturbed.

## Configuration and scope

A per-build configuration adds a second interface claimed only by wardd; builds without it refuse
service requests. With it, write responses to the application carry no leaf, since a copy outside
wardd would go stale.

Work in scope: bind wardd; carry device-initiated exchanges with bounded resources; reads, sync,
publication and queue flush over the channel; recovery routes; reset from the wallet channel.

## Work outline

- **Binding.** wardd opens with a message naming the service protocol version; the device refuses
  other interfaces, builds or versions by name. Binding only records where to send requests;
  readiness comes from a sync when an operation first needs one. It survives a session restart but
  not a power cycle, and re-binding is idempotent. The interface claim is the authorization
  boundary; WARD's own cryptography makes the data trustworthy regardless of carrier.
- **Device-initiated exchanges.** The device is the only initiator, with one request in flight and
  one reader owning the interface. Before binding only the opening is accepted; while a request is
  in flight, only an answer of an expected type. Unsolicited traffic uses a small private buffer;
  size limits and deadlines bound an unauthenticated peer. An unexpected type, timeout or broken
  link fails the operation and drops the binding; wardd recovers by binding again.
- **Reads.** The device derives the keyed path and sends it with its head. wardd answers with the
  sealed entry and proof, or asks for a sync (unauthenticated, so the device syncs and retries once).
  If the read needs freshness the device drives one sync; on failure it falls back to the stored
  head with the freshness warning. wardd learns which paths are read
  ([access and display](../gaps.md#access-and-display)).
- **Sync.** The same round as on the wallet channel
  ([F6.2](f6-freshness.md#f62-implement-nonce-bound-wm-attestation-verification),
  [F6.4](f6-freshness.md#f64-implement-synchronized-head-reconciliation)), driven by the device:
  clear freshness and mint a nonce, obtain the WM challenge, sign the session proof, verify the
  attestation, walk back in bounded pages to the stored head, adopt and settle claims. A WM below
  the device or a chain that misses the stored root fails the sync with nothing persisted.
- **Publication.** The device derives the new root, signs the step
  ([F6.3](f6-freshness.md#f63-sign-wallet-authorized-transitions-for-the-wm)) and clears freshness
  before sending. Each publication uses a fresh nonce. The WM must perform the predecessor check
  and attestation as one operation, and the returned attestation must name exactly the device's own
  step under that nonce; the device then adopts and settles. A publication attestation is
  read-only and leaves the write session in place. A conflict answer means not landed (retry
  hint); any other failure is settled by the next sync
  ([competing writers](../ward_transitions.md#competing-writers)). Queued changes flush one per
  publication.

## Pinning and reset from the wallet channel

The application requests a reset of the service binding over the wallet channel, under the WARD
application role, and the user approves with a held confirmation. While the wallet has unresolved
claims the reset is refused, since only the service that received those changes can settle them; a
forced reset has its own screen naming the count. Reset closes any open service link, drops the
binding and any pin, and clears freshness, so the next wardd proves freshness anew. Nothing stored
is discarded.

## Open questions

- **Authenticated transport.** Should wardd be authenticated (key pinned on first use while
  unlocked) or is the interface claim enough? Authentication adds no cryptographic property and
  costs persistent pin state; without a pin, what does reset mean?
- **Recovery.** The channel has no revert, roll-forward or rejoin, so a regressed WM or incomplete
  wardd history leaves the device stuck there
  ([recovering manager history](../ward_roll_forward.md),
  [recovery and availability](../gaps.md#recovery-and-availability)).
- Whether to add catch-up without a WM, batching and multiple daemons, which exist only on the
  wallet channel or not at all (one wardd per interface; switching requires a reset).

## Related

- [Participants and channels](../ward-channels.md)
- [Transitions and sessions](../ward_transitions.md)
- [Threat model](../threat_model.md) and [security gaps](../gaps.md)
