# WARD Manager

The manager keeps one register per wallet containing the current head and its predecessor.

- **Enrollment.** A wallet device authorizes the starting state at counter zero. A surviving device
  at a later counter cannot use ordinary enrollment to replace a lost register.
- **Attestation.** The manager signs the current step, wallet identity, nonce and time on its clock.
  A live sync binds the response to the device's fresh nonce.
- **Advance.** The manager verifies the wallet's signature for the active write session and checks
  that the proposed change starts at its current head. Acceptance produces a signed receipt.

The register retains only the current step. A later attestation dates that step again, so historical
recovery depends on records kept by the replica. See [recovering manager history](ward_roll_forward.md).

Ordering across failover requires serializing advances and preventing stale manager instances from
continuing to serve. Write sessions and outstanding challenges expire on restart or restore. The
[threat model](threat_model.md#accepted-security-limitations) describes the draft's durability and key provisioning limits.
