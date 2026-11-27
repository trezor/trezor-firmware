# WARD implementation plan

Read the [architecture](architecture.md) first. The work is split into firmware, host,
online-service and Suite tasks. Each task page opens with its design, then describes each subtask.
Host and Suite tasks name the tasks they depend on.

## Firmware

The offline cache comes first, then the trie, entry authentication and confidentiality, chain
history, freshness, and finally rollback and batching. Migration from the miniscript store and the
service channel follow the miniscript release.

- **[F1 Offline cache in miniscript](f1-offline-cache.md)**
  - [F1.1 Implement persistent offline record storage](f1-offline-cache.md#f11-implement-persistent-offline-record-storage)
  - [F1.2 Implement offline add, update, delete and lookup](f1-offline-cache.md#f12-implement-offline-add-update-delete-and-lookup)
  - [F1.3 Add listing and storage capacity handling](f1-offline-cache.md#f13-add-listing-and-storage-capacity-handling)
  - [F1.4 Implement authenticated queue backup export](f1-offline-cache.md#f14-implement-authenticated-queue-backup-export)
  - [F1.5 Implement backup validation and restore](f1-offline-cache.md#f15-implement-backup-validation-and-restore)
  - [F1.6 Connect policy registration and offline reuse](f1-offline-cache.md#f16-connect-policy-registration-and-offline-reuse)
- **[F4 Merkle trie](f4-merkle-trie.md)**
  - [F4.1 Implement canonical leaf and branch hashing](f4-merkle-trie.md#f41-implement-canonical-leaf-and-branch-hashing)
  - [F4.2 Implement membership proof verification](f4-merkle-trie.md#f42-implement-membership-proof-verification)
  - [F4.3 Implement non-membership proof verification](f4-merkle-trie.md#f43-implement-non-membership-proof-verification)
  - [F4.4 Implement insert and update root calculation](f4-merkle-trie.md#f44-implement-insert-and-update-root-calculation)
  - [F4.5 Implement deletion](f4-merkle-trie.md#f45-implement-deletion)
  - [F4.6 Restore verified leaves into the offline queue](f4-merkle-trie.md#f46-restore-verified-leaves-into-the-offline-queue)
  - [F4.8 Listing of all or filtered entries](f4-merkle-trie.md#f48-listing-of-all-or-filtered-entries)
- **[F2 Authenticated entries](f2-authenticated-entries.md)**
  - [F2.1 Implement record identities and derive entry keys](f2-authenticated-entries.md#f21-implement-record-identities-and-derive-entry-keys)
  - [F2.2 Implement identity and content authentication](f2-authenticated-entries.md#f22-implement-identity-and-content-authentication)
  - [F2.3 Add authenticated record messages and test vectors](f2-authenticated-entries.md#f23-add-authenticated-record-messages-and-test-vectors)
- **[F3 Confidential entries](f3-confidential-entries.md)**
  - [F3.1 Derive offline cache encryption keys](f3-confidential-entries.md#f31-derive-offline-cache-encryption-keys)
  - [F3.2 Encrypt and decrypt offline cache entries](f3-confidential-entries.md#f32-encrypt-and-decrypt-offline-cache-entries)
  - [F3.3 Release application keys on demand (post-MVP)](f3-confidential-entries.md#f33-release-application-keys-on-demand-post-mvp)
- **[F5 Chain history verification](f5-chain-history.md)**
  - [F5.1 Implement authenticated transition records](f5-chain-history.md#f51-implement-authenticated-transition-records)
  - [F5.2 Implement complete chain verification and adoption](f5-chain-history.md#f52-implement-complete-chain-verification-and-adoption)
  - [F5.3 Add bounded history transfer and interruption handling](f5-chain-history.md#f53-add-bounded-history-transfer-and-interruption-handling)
  - [F5.4 Offline sync corner cases](f5-chain-history.md#f54-offline-sync-corner-cases)
- **[F6 Firmware freshness and latest counter](f6-freshness.md)**
  - [F6.1 Implement durable per-wallet trusted heads](f6-freshness.md#f61-implement-durable-per-wallet-trusted-heads)
  - [F6.2 Implement nonce-bound WM attestation verification](f6-freshness.md#f62-implement-nonce-bound-wm-attestation-verification)
  - [F6.3 Sign wallet-authorized transitions for the WM](f6-freshness.md#f63-sign-wallet-authorized-transitions-for-the-wm)
  - [F6.4 Implement synchronized head reconciliation](f6-freshness.md#f64-implement-synchronized-head-reconciliation)
  - [F6.5 Reject stale counters, roots and attestations](f6-freshness.md#f65-reject-stale-counters-roots-and-attestations)
  - [F6.6 Verify atomic updates and power-loss recovery](f6-freshness.md#f66-verify-atomic-updates-and-power-loss-recovery)
- **[F7 Rollback and batching](f7-rollback-batching.md)**
  - [F7.1 Implement persistent pending edit management](f7-rollback-batching.md#f71-implement-persistent-pending-edit-management)
  - [F7.2 Prepare and validate batch transitions](f7-rollback-batching.md#f72-prepare-and-validate-batch-transitions)
  - [F7.3 Implement batch confirmation and cancellation](f7-rollback-batching.md#f73-implement-batch-confirmation-and-cancellation)
  - [F7.4 Authorize reverts with monotonic counters](f7-rollback-batching.md#f74-authorize-reverts-with-monotonic-counters)
  - [F7.5 Implement fork and missing-history recovery](f7-rollback-batching.md#f75-implement-fork-and-missing-history-recovery)
  - [F7.6 Protect recovery against authorization replay](f7-rollback-batching.md#f76-protect-recovery-against-authorization-replay)
- **[F8 Migration from the miniscript store](f8-migration.md)**
- **[F9 Service channel](f9-service-channel.md)**

## Host and wardd

- **[H1 wardd and host adapter](h1-wardd-host-adapter.md)**
  - [H1.1 Implement wardd request routing and conversation lifecycle](h1-wardd-host-adapter.md#h11-implement-wardd-request-routing-and-conversation-lifecycle)
  - [H1.2 Build the shared Rust forwarding adapter](h1-wardd-host-adapter.md#h12-build-the-shared-rust-forwarding-adapter)
  - [H1.3 Add Python bindings and Jade host integration](h1-wardd-host-adapter.md#h13-add-python-bindings-and-jade-host-integration)
  - [H1.4 Add TypeScript bindings and Connect integration](h1-wardd-host-adapter.md#h14-add-typescript-bindings-and-connect-integration)
  - [H1.5 Connect the adapter to Liana host sessions](h1-wardd-host-adapter.md#h15-connect-the-adapter-to-liana-host-sessions)
- **[H2 Host trie reconstruction](h2-host-trie.md)** (depends on F4, H1)
  - [H2.1 Build the canonical host trie from records](h2-host-trie.md#h21-build-the-canonical-host-trie-from-records)
  - [H2.2 Generate membership and non-membership proofs](h2-host-trie.md#h22-generate-membership-and-non-membership-proofs)
  - [H2.3 Apply stored insert, update and delete transitions](h2-host-trie.md#h23-apply-stored-insert-update-and-delete-transitions)
  - [H2.4 Match host roots and proofs against firmware](h2-host-trie.md#h24-match-host-roots-and-proofs-against-firmware)
- **[H3 History reconstruction](h3-history-reconstruction.md)** (depends on H2, F5)
  - [H3.1 Walk backward from the authoritative head](h3-history-reconstruction.md#h31-walk-backward-from-the-authoritative-head)
  - [H3.2 Replay selected history and check intermediate roots](h3-history-reconstruction.md#h32-replay-selected-history-and-check-intermediate-roots)
- **[H5 wardd online sync](h5-wardd-online-sync.md)** (depends on H4, F6, H3)
  - [H5.1 Integrate authoritative WM heads into synchronization](h5-wardd-online-sync.md#h51-integrate-authoritative-wm-heads-into-synchronization)
  - [H5.2 Persist candidates before WM publication and finalization](h5-wardd-online-sync.md#h52-persist-candidates-before-wm-publication-and-finalization)
  - [H5.3 Resume device catch-up after disconnection](h5-wardd-online-sync.md#h53-resume-device-catch-up-after-disconnection)
  - [H5.4 Expose pending edit batch and revert operations](h5-wardd-online-sync.md#h54-expose-pending-edit-batch-and-revert-operations)
  - [H5.5 Implement fork rejoin and recovery coordination](h5-wardd-online-sync.md#h55-implement-fork-rejoin-and-recovery-coordination)
  - [H5.6 Expose synchronization status and recovery actions](h5-wardd-online-sync.md#h56-expose-synchronization-status-and-recovery-actions)

## Online services

The WARD Manager extends the Quota Manager of the Suite Sync service, and WARD's records are stored
through the same service's relay.

- **[H4 WARD manager service](h4-ward-manager-service.md)** (depends on H2.4)
  - [H4.1 Build service routing configuration and health checks](h4-ward-manager-service.md#h41-build-service-routing-configuration-and-health-checks)
  - [H4.2 Persist wallet heads and transition history](h4-ward-manager-service.md#h42-persist-wallet-heads-and-transition-history)
  - [H4.3 Prevent conflicting head updates](h4-ward-manager-service.md#h43-prevent-conflicting-head-updates)
  - [H4.4 Verify wallet transition signatures](h4-ward-manager-service.md#h44-verify-wallet-transition-signatures)
  - [H4.5 Sign fresh challenge-bound head attestations](h4-ward-manager-service.md#h45-sign-fresh-challenge-bound-head-attestations)
  - [H4.6 Expose ordered history and idempotent retries](h4-ward-manager-service.md#h46-expose-ordered-history-and-idempotent-retries)
  - [H4.7 Implement head nonce rotation and recovery generations](h4-ward-manager-service.md#h47-implement-head-nonce-rotation-and-recovery-generations)
  - [H4.8 Provision service signing and firmware trust keys](h4-ward-manager-service.md#h48-provision-service-signing-and-firmware-trust-keys)
  - [H4.9 Implement backup restore and stale-instance protection](h4-ward-manager-service.md#h49-implement-backup-restore-and-stale-instance-protection)
  - [H4.10 Deploy staging with health metrics and limits](h4-ward-manager-service.md#h410-deploy-staging-with-health-metrics-and-limits)
- **[H7 WARD storage on Suite Sync](h7-ward-storage-on-suite-sync.md)** (depends on H4, H5)
  - [H7.1 Register the WARD owner with the Quota Manager](h7-ward-storage-on-suite-sync.md#h71-register-the-ward-owner-with-the-quota-manager)
  - [H7.2 Allocate and account quota for WARD records](h7-ward-storage-on-suite-sync.md#h72-allocate-and-account-quota-for-ward-records)
  - [H7.3 Configure wardd's relay endpoint and credentials](h7-ward-storage-on-suite-sync.md#h73-configure-wardds-relay-endpoint-and-credentials)
  - [H7.4 Handle quota exhaustion and refusal](h7-ward-storage-on-suite-sync.md#h74-handle-quota-exhaustion-and-refusal)

## Suite

- **[S1 Suite backup UX](s1-suite-backup-ux.md)** (depends on F3)
  - [S1.1 Build Suite policy registration and offline views](s1-suite-backup-ux.md#s11-build-suite-policy-registration-and-offline-views)
  - [S1.2 Build Suite backup and restore actions](s1-suite-backup-ux.md#s12-build-suite-backup-and-restore-actions)
- **[H6 Suite WARD UX](h6-suite-ward-ux.md)** (depends on H5, F3, F7, S1)
  - [H6.1 List WARD entries and applications](h6-suite-ward-ux.md#h61-list-ward-entries-and-applications)
  - [H6.2 Request application keys](h6-suite-ward-ux.md#h62-request-application-keys)
  - [H6.3 Manage WARD entries](h6-suite-ward-ux.md#h63-manage-ward-entries)
  - [H6.4 Review pending edits and batches](h6-suite-ward-ux.md#h64-review-pending-edits-and-batches)
  - [H6.5 Show synchronization and recovery actions](h6-suite-ward-ux.md#h65-show-synchronization-and-recovery-actions)
  - [H6.6 Decrypt selected WARD leaves](h6-suite-ward-ux.md#h66-decrypt-selected-ward-leaves)
  - [H6.7 Verify Merkle proofs before manual restore](h6-suite-ward-ux.md#h67-verify-merkle-proofs-before-manual-restore)
  - [H6.8 Manually restore entries into the offline queue](h6-suite-ward-ux.md#h68-manually-restore-entries-into-the-offline-queue)

## Open questions

Undecided design points are listed at the end of each page:
[architecture](architecture.md#open-questions), [F1](f1-offline-cache.md#open-questions),
[F4](f4-merkle-trie.md#open-questions), [F6](f6-freshness.md#open-questions),
[F7](f7-rollback-batching.md#open-questions),
[F8](f8-migration.md#open-questions), [F9](f9-service-channel.md#open-questions),
[H1](h1-wardd-host-adapter.md#open-questions), [H3](h3-history-reconstruction.md#open-questions),
[H4](h4-ward-manager-service.md#open-questions), [H5](h5-wardd-online-sync.md#open-questions),
[H6](h6-suite-ward-ux.md#open-questions) and [S1](s1-suite-backup-ux.md#open-questions).
