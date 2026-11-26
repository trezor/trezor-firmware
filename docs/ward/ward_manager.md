# WARD Manager

The manager keeps one register per wallet containing the current head and its predecessor.

- **Enrollment.** A wallet device authorizes the starting state at counter zero. A surviving device
  at a later counter cannot use ordinary enrollment to replace a lost register.
- **Attestation.** The manager signs the current step, wallet identity, nonce and time on its clock.
  A live sync binds the response to the device's fresh nonce.
- **Advance.** The manager verifies the wallet's signature for the active write session and checks
  that the proposed change starts at its current head. Acceptance produces a signed receipt.

WARD manager retains only the latest step. 


