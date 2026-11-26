# Proposed migration from mini-WARD to MVP

Public mini-WARD stores records on each Trezor, scoped to its passphrase wallet and application.
The MVP overlaps some of that protected storage. A safe upgrade needs a separate destination so
the device can still read the originals. Some legacy records also exceed the MVP queue's capacity.

1. After unlock, the device reads the active wallet's records in their original application and
   subscope. Once the user enables replication, it checks each eligible destination against its
   trusted root and seals the value. Unsupported, oversized and device-local records stay local.
2. A matching destination value can settle the import. A different value requires a user decision.
3. The device records progress after adoption. An interrupted import must resume without duplicating
   a write or recreating an entry the user removed.

Each Trezor keeps its own source records until processed. Using one writer per wallet during import
avoids competing branches. Automatic migration remains a proposal.
