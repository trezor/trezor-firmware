"""WARD: the decomposed AuthDbUpdateLeaf write round + sync/lookup flows.

The trust-anchor logic (MPT proofs, WM attestation verification, wallet/MAC
derivation, the pending-edit queue, and the write/lookup/sync orchestration)
lives in a single module, apps.ward.service (TW). The other modules in this
package are thin host-facing protobuf handlers (TA) that marshal wire messages
to/from Core (apps.common.ward), which gates access by app capability before
calling apps.ward.service. Persistence lives in storage.ward_store.
"""
