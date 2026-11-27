# F5 Chain history verification

The Trezor stores one head per wallet (counter, root, and the manager's signed time when attested)
and adopts a newer head only after verifying every transition in between. Hosts keep transitions;
the WM orders them, keeps only the latest step per wallet and attests the current head; only a
wallet device can authorize a step.

- A commit advances the counter by its change count (1 to 8), a revert by exactly 1
  ([counter rules](../ward_transitions.md#why-commits-count-changes-and-reverts-count-one)).
- The stored head moves only after a complete walk; refused or interrupted walks change nothing.

## F5.1 Implement authenticated transition records

A transition covers the wallet's public identifier, the from and to (counter, root), and a commit
or revert kind; the empty tree uses its fixed constant. The device produces over the same bytes a
**wallet authentication tag** (HMAC-SHA256, device-only key, the sole authority on state) and a
**publication signature** (Ed25519, bound to the current WM write session; in the MVP wardd checks
it) ([sessions](../ward_transitions.md#sessions)). Verifiers try both kinds in constant time.

Signing does not adopt: the device stays at the old head and clears freshness. Authorizing a revert
ends the write session; a new sync is required before anything else is authorized.

## F5.2 Implement complete chain verification and adoption

From the anchor (with a WM, the transition attested in this round, bound to the device's nonce),
walk backwards: request the record ending exactly at the running state, check the step size, verify
the tag, continue from its start. The first record must start at the attested predecessor; the walk
must land exactly on the stored counter and root. A one-step anchor needs only the tag.

Records of unaccepted writes cannot enter. A lower anchor is never adopted; the same counter with
another root is a fork needing a [rejoin](../ward_roll_forward.md#reverting-and-rejoining). Crossed
reverts are reported, not gated.

Adopt in order: settle queued changes against crossed tags, persist head and time, set freshness,
drop any session-only head, close the round. A cut between settling and persisting is a known gap
([settle, then save](../gaps.md#publication-and-reads)).

## F5.3 Add bounded history transfer and interruption handling

Each request names the exact state the next record must end at; replies may carry several records,
newest first, up to a fixed cap. The device keeps only the running state, revert count and crossed
tags matching open claims, so memory is constant. Nothing persists until the walk completes; the
round lives in the session, so a disconnect or power loss discards it, and a new sync replaces the
round and nonce. An interrupted walk restarts, never resumes from a saved cursor. Reply deadlines
bound a stalled host.

## F5.4 Offline sync corner cases

| Situation | Device behaviour |
| --- | --- |
| WM unreachable, cached attestation of N | Verify the signature, then walk to M from the attested predecessor. By default N is a session-only read position shown with its signed date. |
| Same, persistence option on | Persist N without freshness; a missed revert can leave it on a discarded branch ([verified read](../threat_model.md#what-a-verified-read-means)). |
| Cached attestation in a live session | Refused. |
| MVP without WM | Chain alone decides; head always persisted. |
| Host behind the WM | Walk fails; stay at M ([data loss](../ward-trie.md#recovery-after-data-loss-in-evolu)). |
| Head below the stored one | Refused before any record. |
| WM attests below the device | Not adopted; report the WM is behind ([roll-forward](../ward_roll_forward.md#evidence-for-each-step)). |
| Same counter, other root | Fork; only a rejoin switches. |
| Revert between M and N | Accepted; reverts reported. |
| Publication reply lost | Stay at M; a queued change settles only when its own tag is crossed; lost races use the [retry path](../ward_transitions.md#competing-writers). |
| New write session after an unlanded write | The old authorization can no longer land; a read-only attestation leaves it valid. |

A head reached without a live attestation never sets freshness and never bases a write.
