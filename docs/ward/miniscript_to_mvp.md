# Migrating mini-WARD to WARD MVP

Proposed design for a firmware upgrade from the on-device mini-WARD in public firmware
to the replicated WARD MVP without a WARD Manager (WM). The upgrade keeps existing
records usable on the same device. Eligible data is sealed and published in the background
once the user enables WARD sync and the device can reach wardd.

## Source and destination

This design uses public [firmware main at `95f789708e`](https://github.com/trezor/trezor-firmware/tree/95f789708e726fce68cb3e479b5d4fbde42918ab)
as the source baseline. The mini-WARD store has the same version-0 record layout on the
checked [`jjanku/ward/trie` tip](https://github.com/trezor/trezor-firmware/tree/2f12ddcdd64b1dff64cc096f97071c862095442f).
The destination is the no-WM build on `petrsusil/ward-draft`.

| | Public mini-WARD | WARD MVP |
| --- | --- | --- |
| Stored data | A local map scoped by passphrase wallet, app and optional subscope. A protected storage slot holds a version-0 record with a wallet-ID prefix, app bytes, key and value. | Sealed leaves and authenticated transitions in wardd/Evolu. The device persists the adopted root plus offline copies and queued intents. |
| Identity | The original wallet ID is derived under `TREZOR / WARD / Wallet ID`. App and subscope identifiers are binary. | The draft derives a different local wallet ID. A leaf uses the MVP application namespace, identifier and device scope, with entry type encoded in sealed content. |
| Limits | Up to 32 records, 8,192 bytes in total and 2,560 bytes per record including the header. | The draft offline store holds up to 20 records, with a 6,144-byte budget and a per-value limit of 1,024 bytes. Each mapped record must also fit its destination's wire and leaf limits. |

Sources for the public format and identity rules are the [Rust store](https://github.com/trezor/trezor-firmware/blob/95f789708e726fce68cb3e479b5d4fbde42918ab/core/embed/rust/src/ward/store.rs),
the [app and subscope API](https://github.com/trezor/trezor-firmware/blob/95f789708e726fce68cb3e479b5d4fbde42918ab/core/src/apps/ward/store.py),
and the [wallet ID derivation](https://github.com/trezor/trezor-firmware/blob/95f789708e726fce68cb3e479b5d4fbde42918ab/core/src/apps/ward/keys.py).
See also the MVP [leaf format](ward-leaf.md).

### Resolve the flash key collision first

Both implementations use the protected `APP_WARD` namespace (`0x05`). Public mini-WARD
uses slot keys `0x00` through `0x1f`. The draft MVP assigns keys in that range to roots,
host pins, and wallet settings. On an upgraded device, a normal MVP write can therefore
overwrite a source record before any migration runs.

Move the MVP layout to disjoint storage keys before enabling MVP on devices that may
hold public mini-WARD records. Reserve the full legacy range and retain a read-only
legacy reader outside the MVP layout. If a draft MVP layout has already been deployed,
recognize it by trusted provenance and migrate it separately. Cover the case where a
legacy slot contains bytes that resemble MVP metadata. Account for storage limits and
interrupted updates before retiring any legacy slots.

## On-device migration

1. **Keep local reads available.** Read legacy records only after unlock, using the
   original wallet ID derivation for the active passphrase and the original app/subscope
   rules. Preserve the app's access to its records during the upgrade. A host cannot
   choose the source wallet, scope, key or value.
2. **Map identities explicitly.** Define a mapping for each supported source app and
   record type. Specify the destination application namespace, identifier, entry type,
   and wallet-wide or device-local scope. Preserve binary identifiers byte-for-byte
   where the mapping calls for it. Keep unknown records in legacy storage until their
   owning app defines a mapping. Keep records that are intentionally device-local out
   of replication.
3. **Publish eligible records through the existing MVP write path.** Once WARD sync is
   enabled, establish the device's trusted MVP head with `WardCatchUp`. For each
   eligible record, derive its target path on the Trezor, verify the target's value or
   absence against the trusted root, and seal any new leaf on-device. Send wardd the
   ordinary sealed change and authenticated transition. This path can stream one
   record at a time and avoid using one queue slot per legacy record.
4. **Settle only after device adoption.** wardd appends the change and the device
   verifies and adopts the result through normal catch-up. Mark the record migrated
   only when the device has verified the destination value or its exact transition on
   the adopted chain. Journal the record and its outstanding transition in protected
   storage so a retry can recognize an adopted write. A repeated run with the same
   adopted value completes without publishing it twice. Keep the source until migration
   is durable enough for recovery under the rollout's retention policy.

The ordinary path needs no per-record confirmation after the user has enabled sync for
that data. A different value already present at the target requires the normal conflict
flow. An explicit legacy erase or user choice to keep the MVP value must also be reflected
in migration progress so a retry cannot bring back an old value. The host receives sealed
records and the usual routing metadata. The migration keeps plaintext, legacy wallet
IDs, and seed material on the device.

## Rollout and tests

- **Source coverage.** Build upgrade fixtures with the public firmware implementation.
  Cover multiple passphrases, app subscopes, binary keys and values, and occupied legacy
  slots where the draft currently places roots, pins, or settings.
- **Capacity and unsupported types.** Use a full 32-slot source and a record that exceeds
  the MVP queue or leaf limits. An entry that cannot be copied remains accessible at its
  source. Report incomplete migration without eviction or truncation.
- **Restart and retry.** Interrupt the upgrade and interrupt migration before append,
  after append, and after device adoption. Verify persistence across reboot and absence
  of duplicate writes. Verify local access when wardd or the relay is unavailable.
- **Conflicts and multiple devices.** Check equal and different destination values,
  deletion after successful import, and an existing MVP fork. Use one writer for a
  given MVP wallet during import. Retain each device's legacy records when it holds
  independent data.
- **Downstream compatibility.** After migration, read the sealed record through normal
  MVP proofs. The resulting history uses ordinary MVP links and can carry forward
  through the [MVP-to-WM migration](mvp_to_final_migration.md).
