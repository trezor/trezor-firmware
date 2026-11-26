# Checking the trust boundaries

| Check | Expected result |
| --- | --- |
| Proof from a different root | The device refuses the entry or absence claim. |
| Write authorized in a retired session | The manager refuses it even if the head is unchanged. |
| Archived attestation offered during live sync | The signature fails the fresh challenge. |
| Recovery step with only wallet authorization | The device requires a manager record before releasing a new authorization. |

The [adversarial test runbook](../../tests/ward/ward_adversarial_testing.md) describes these checks.
The [threat model](threat_model.md#accepted-security-limitations) covers cases a device cannot detect.
