# Verifying WARD

Tree tests compare a device's incremental updates with a host's independent reconstruction,
including deletion of the last entry. Manager tests cover enrollment, competing writers and session
replacement. Device tests cover freshness after signing, approval of conflicting retries, and
withholding recovery signatures when the user declines.

The [test runbook](../../tests/ward/ward_testing.md) describes the environments and procedures.
