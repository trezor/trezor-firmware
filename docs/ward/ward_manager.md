# WARD Manager

The manager keeps one register per wallet containing the current head and its predecessor.

- **Enrollment.** A wallet device authorizes the starting state at counter zero. A surviving device
  at a later counter cannot use ordinary enrollment to replace a lost register.
- **Attestation.** The manager signs the current step, wallet identity, nonce and time on its clock.
  A live sync binds the response to the device's fresh nonce.
- **Advance.** The manager verifies the wallet's signature for the active write session and checks
  that the proposed change starts at its current head. Acceptance produces a signed receipt.

WARD manager retains only the latest step. 

## Catching up a second Trezor

If a second Trezor remembers head M and the manager attests a newer head N, so M < N, the host
supplies the intervening wallet-authorized steps. The device walks back from N until it reaches the
exact counter **and root** it stored at M. A different root at M means the histories diverged.
Switching branches requires a [rejoin](ward_roll_forward.md#reverting-and-rejoining).

When the manager is unreachable, the host can instead offer a head with a cached attestation.
The device checks its signature, rejects a signed time earlier than its stored one when available,
and verifies the same chain back to its own head. By default this gives the device a read position
for the session. Its stored head stays at M for the next live sync. See the
[offline persistence option](threat_model.md#what-a-verified-read-means).
